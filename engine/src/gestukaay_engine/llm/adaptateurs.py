"""Un adaptateur par format d'API. Chacun reçoit (système, utilisateur, schéma)
et renvoie un Brut : le texte produit et la comptabilité de l'appel.

Aucun SDK : de simples requêtes httpx, pour rester neutre vis-à-vis des
fournisseurs. Les erreurs sont traduites en ErreurAdaptateur(statut), pour
que la chaîne sache pourquoi elle passe au maillon suivant.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace

import httpx

from .base import Brut, ErreurAdaptateur, Maillon

URL_OPENROUTER = "https://openrouter.ai/api/v1"
URL_ANTHROPIC = "https://api.anthropic.com/v1"
URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta"
URL_HUGGINGFACE = "https://router.huggingface.co/v1"


def consigne_json(schema: dict) -> str:
    """Rappel ajouté au message système quand le fournisseur ne contraint pas le JSON lui-même."""
    return ("\n\nRéponds UNIQUEMENT par un objet JSON valide, sans texte autour, conforme à ce "
            "schéma JSON :\n" + json.dumps(schema, ensure_ascii=False))


def _message_erreur(r: httpx.Response) -> str:
    """Le message lisible d'une erreur HTTP, quel que soit le format du fournisseur."""
    try:
        d = r.json()
    except ValueError:
        return " ".join(r.text.split())[:200]
    e = d.get("error", d) if isinstance(d, dict) else d
    if isinstance(e, dict):
        return str(e.get("message") or e.get("type") or e)[:200]
    return str(e)[:200]


def _poster(client: httpx.Client, url: str, entetes: dict, corps: dict) -> dict:
    try:
        r = client.post(url, headers=entetes, json=corps)
    except httpx.TimeoutException as e:
        raise ErreurAdaptateur("delai", type(e).__name__) from e
    except httpx.HTTPError as e:
        raise ErreurAdaptateur("reseau", type(e).__name__) from e
    if r.status_code != 200:
        raise ErreurAdaptateur("http", f"{r.status_code} {_message_erreur(r)}")
    try:
        return r.json()
    except ValueError as e:
        raise ErreurAdaptateur("http", "réponse non JSON") from e


# --------------------------------------------------------------------------
# Format « OpenAI compatible » : OpenRouter, OpenAI, Mistral, Groq, Ollama…
# --------------------------------------------------------------------------

def openai_compatible(client: httpx.Client, m: Maillon, systeme: str, utilisateur: str, schema: dict) -> Brut:
    mode = m.mode_json or "objet"  # json_object est le plus largement supporté
    corps: dict = {
        "model": m.modele,
        "messages": [
            {"role": "system", "content": systeme if mode == "schema" else systeme + consigne_json(schema)},
            {"role": "user", "content": utilisateur},
        ],
    }
    if m.temperature is not None:
        corps["temperature"] = m.temperature
    if mode == "schema":
        corps["response_format"] = {"type": "json_schema",
                                    "json_schema": {"name": "reponse", "schema": schema}}
    elif mode == "objet":
        corps["response_format"] = {"type": "json_object"}
    base = (m.url or URL_OPENROUTER).rstrip("/")
    if "openrouter.ai" in base:
        corps["usage"] = {"include": True}  # OpenRouter renvoie alors le coût exact
    entetes = {"Authorization": f"Bearer {m.cle}"} if m.cle else {}
    d = _poster(client, f"{base}/chat/completions", entetes, corps)
    try:
        choix = d["choices"][0]
        texte = choix["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise ErreurAdaptateur("http", "réponse sans choices[0].message") from e
    if choix.get("finish_reason") == "content_filter":
        raise ErreurAdaptateur("refus", "content_filter")
    u = d.get("usage") or {}
    return Brut(texte=texte, jetons_entree=u.get("prompt_tokens"), jetons_sortie=u.get("completion_tokens"),
                cout_usd=u.get("cost"), modele=d.get("model") or m.modele)


# --------------------------------------------------------------------------
# Anthropic (API Messages, en direct)
# --------------------------------------------------------------------------

# Mots-clés de JSON Schema refusés par la sortie structurée d'Anthropic : on les
# retire avant l'envoi ; la validation Pydantic chez nous les revérifie.
_NON_SUPPORTES = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
                  "minLength", "maxLength", "minItems", "maxItems", "default", "examples"}


def schema_pour_anthropic(schema: dict) -> dict | None:
    """Schéma compatible avec la sortie structurée Anthropic, ou None si impossible
    (objet à clés libres : additionalProperties doit valoir false partout)."""
    s = copy.deepcopy(schema)

    def nettoyer(n):
        if isinstance(n, dict):
            for k in _NON_SUPPORTES & n.keys():
                del n[k]
            if n.get("type") == "object" or "properties" in n:
                if n.get("additionalProperties", False) is not False:
                    raise ValueError("objet à clés libres")
                n["additionalProperties"] = False
            for v in n.values():
                nettoyer(v)
        elif isinstance(n, list):
            for v in n:
                nettoyer(v)

    try:
        nettoyer(s)
    except ValueError:
        return None
    return s


def anthropic(client: httpx.Client, m: Maillon, systeme: str, utilisateur: str, schema: dict) -> Brut:
    natif = schema_pour_anthropic(schema) if (m.mode_json or "schema") == "schema" else None
    corps: dict = {
        "model": m.modele,
        "max_tokens": 1024,
        "system": systeme if natif else systeme + consigne_json(schema),
        "messages": [{"role": "user", "content": utilisateur}],
    }
    if natif:
        corps["output_config"] = {"format": {"type": "json_schema", "schema": natif}}
    if m.temperature is not None:
        corps["temperature"] = m.temperature
    entetes = {"x-api-key": m.cle, "anthropic-version": "2023-06-01"}
    d = _poster(client, f"{(m.url or URL_ANTHROPIC).rstrip('/')}/messages", entetes, corps)
    if d.get("stop_reason") == "refusal":
        raise ErreurAdaptateur("refus", str((d.get("stop_details") or {}).get("category")))
    texte = "".join(b.get("text", "") for b in d.get("content") or [] if b.get("type") == "text")
    u = d.get("usage") or {}
    return Brut(texte=texte, jetons_entree=u.get("input_tokens"), jetons_sortie=u.get("output_tokens"),
                modele=d.get("model") or m.modele)


# --------------------------------------------------------------------------
# Google Gemini (generateContent, en direct)
# --------------------------------------------------------------------------

def gemini(client: httpx.Client, m: Maillon, systeme: str, utilisateur: str, schema: dict) -> Brut:
    config: dict = {}
    if (m.mode_json or "objet") != "aucun":
        config["responseMimeType"] = "application/json"
    if m.temperature is not None:
        config["temperature"] = m.temperature
    corps = {
        "systemInstruction": {"parts": [{"text": systeme + consigne_json(schema)}]},
        "contents": [{"role": "user", "parts": [{"text": utilisateur}]}],
        "generationConfig": config,
    }
    url = f"{(m.url or URL_GEMINI).rstrip('/')}/models/{m.modele}:generateContent"
    d = _poster(client, url, {"x-goog-api-key": m.cle}, corps)
    try:
        cand = d["candidates"][0]
    except (KeyError, IndexError, TypeError) as e:
        bloque = (d.get("promptFeedback") or {}).get("blockReason")
        raise ErreurAdaptateur("refus" if bloque else "http", bloque or "aucun candidat") from e
    if cand.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "RECITATION"):
        raise ErreurAdaptateur("refus", cand["finishReason"])
    texte = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts") or [])
    u = d.get("usageMetadata") or {}
    sortie = (u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0)
    return Brut(texte=texte, jetons_entree=u.get("promptTokenCount"), jetons_sortie=sortie or None,
                modele=d.get("modelVersion") or m.modele)


# --------------------------------------------------------------------------
# Hugging Face (Inference Providers) : format OpenAI compatible
# --------------------------------------------------------------------------

def huggingface(client: httpx.Client, m: Maillon, systeme: str, utilisateur: str, schema: dict) -> Brut:
    """Routeur Hugging Face. Le modèle peut choisir l'hébergeur : « org/modele:groq »,
    « org/modele:fastest » ou « :cheapest ». Les hébergeurs ne gèrent pas tous le mode
    JSON : par défaut, consigne dans le prompt (JSON revalidé chez nous de toute façon).
    Pour un Inference Endpoint dédié (TGI, vLLM) : LLM_<NOM>_URL=https://<endpoint>/v1."""
    m = replace(m, url=m.url or URL_HUGGINGFACE, mode_json=m.mode_json or "aucun")
    return openai_compatible(client, m, systeme, utilisateur, schema)


ADAPTATEURS = {"openai_compatible": openai_compatible, "huggingface": huggingface,
               "anthropic": anthropic, "gemini": gemini}
