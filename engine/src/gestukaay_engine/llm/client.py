"""Client LLM multi-fournisseur : une chaîne de maillons essayés dans l'ordre.

    client = charger_client()                      # depuis les variables d'environnement
    requete, appel = client.structurer(systeme, question, RequeteStructuree)

Chaque maillon a son délai (2 s par défaut, cahier 10.4). Un maillon échoue
sur : délai dépassé, erreur réseau ou HTTP, refus du fournisseur, JSON
illisible, ou JSON non conforme au schéma Pydantic. On passe alors au suivant.
Si tous échouent : EchecLLM, et le moteur répond « incompréhension ».

Le dernier recours peut être un maillon « regles » : une fonction locale,
sans réseau ni modèle (lexique + référentiel), branchée par le moteur (#10, #22).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .adaptateurs import ADAPTATEURS
from .base import Appel, Brut, EchecLLM, ErreurAdaptateur, Maillon, Tentative

M = TypeVar("M", bound=BaseModel)
# Fournisseurs qui exigent une clé (openai_compatible non : Ollama local n'en a pas)
CLE_OBLIGATOIRE = {"gemini", "anthropic", "huggingface"}
# Secours local : (système, utilisateur) -> dict, ou None si les règles ne savent pas répondre
Regles = Callable[[str, str], dict | None]


class ClientLLM:
    def __init__(self, chaine: list[Maillon], regles: Regles | None = None,
                 transport: httpx.BaseTransport | None = None):
        if not chaine:
            raise ValueError("chaîne LLM vide : définir LLM_CHAINE")
        self.chaine = chaine
        self.regles = regles
        self._transport = transport  # tests : httpx.MockTransport

    def structurer(self, systeme: str, utilisateur: str, modele: type[M]) -> tuple[M, Appel]:
        schema = modele.model_json_schema()
        appel = Appel()
        for m in self.chaine:
            debut = time.perf_counter()
            try:
                brut = self._appeler(m, systeme, utilisateur, schema)
                objet = self._valider(brut.texte, modele)
            except ErreurAdaptateur as e:
                appel.tentatives.append(self._tentative(m, e.statut, debut, str(e)))
                continue
            t = self._tentative(m, "ok", debut)
            appel.tentatives.append(t)
            appel.maillon, appel.fournisseur, appel.modele = m.nom, m.fournisseur, brut.modele or m.modele
            appel.jetons_entree, appel.jetons_sortie = brut.jetons_entree, brut.jetons_sortie
            appel.cout_usd = brut.cout_usd if brut.cout_usd is not None else self._cout(m, brut)
            appel.latence_ms = sum(x.latence_ms for x in appel.tentatives)
            return objet, appel
        appel.latence_ms = sum(x.latence_ms for x in appel.tentatives)
        raise EchecLLM(appel)

    # ------------------------------------------------------------------

    def _appeler(self, m: Maillon, systeme: str, utilisateur: str, schema: dict) -> Brut:
        if m.fournisseur == "regles":
            if self.regles is None:
                raise ErreurAdaptateur("indisponible", "aucune règle locale branchée")
            d = self.regles(systeme, utilisateur)
            if d is None:
                raise ErreurAdaptateur("indisponible", "règles sans réponse")
            return Brut(texte=json.dumps(d, ensure_ascii=False), modele="regles")
        if not m.cle and m.fournisseur in CLE_OBLIGATOIRE:
            raise ErreurAdaptateur("indisponible", f"clé absente : définir LLM_{m.nom.upper()}_CLE")
        with httpx.Client(timeout=m.delai_s, transport=self._transport) as client:
            return ADAPTATEURS[m.fournisseur](client, m, systeme, utilisateur, schema)

    @staticmethod
    def _valider(texte: str, modele: type[M]) -> M:
        t = texte.strip()
        if t.startswith("```"):  # certains modèles entourent le JSON d'un bloc de code
            t = t.strip("`").removeprefix("json").strip()
        try:
            donnees = json.loads(t)
        except ValueError as e:
            raise ErreurAdaptateur("json", t[:120]) from e
        try:
            return modele.model_validate(donnees)
        except ValidationError as e:
            raise ErreurAdaptateur("schema", str(e.errors()[:2])) from e

    @staticmethod
    def _tentative(m: Maillon, statut: str, debut: float, detail: str = "") -> Tentative:
        return Tentative(maillon=m.nom, fournisseur=m.fournisseur, modele=m.modele, statut=statut,
                         latence_ms=round((time.perf_counter() - debut) * 1000), detail=detail[:300])

    @staticmethod
    def _cout(m: Maillon, b: Brut) -> float | None:
        if m.prix_entree is None or m.prix_sortie is None or b.jetons_entree is None:
            return None
        return (b.jetons_entree * m.prix_entree + (b.jetons_sortie or 0) * m.prix_sortie) / 1e6


# --------------------------------------------------------------------------
# Configuration par variables d'environnement
# --------------------------------------------------------------------------

def _flottant(v: str | None) -> float | None:
    return float(v) if v not in (None, "") else None


def lire_chaine(env: Mapping[str, str] = os.environ) -> list[Maillon]:
    """LLM_CHAINE=principal,repli,secours puis, pour chaque nom N :
    LLM_N_FOURNISSEUR, LLM_N_MODELE, LLM_N_CLE, LLM_N_URL, LLM_N_DELAI_S,
    LLM_N_TEMPERATURE (« aucune » pour ne pas l'envoyer), LLM_N_JSON,
    LLM_N_PRIX_ENTREE, LLM_N_PRIX_SORTIE ($ par million de jetons),
    LLM_N_HEBERGEURS (OpenRouter : « cerebras,groq »), LLM_N_TRI (« latency »…)."""
    noms = [n.strip() for n in env.get("LLM_CHAINE", "").split(",") if n.strip()]
    delai_defaut = float(env.get("LLM_DELAI_S", "2"))
    chaine = []
    for nom in noms:
        p = f"LLM_{nom.upper()}_"
        fournisseur = env.get(p + "FOURNISSEUR", "")
        if fournisseur not in (*ADAPTATEURS, "regles"):
            raise ValueError(f"{p}FOURNISSEUR invalide : {fournisseur!r} "
                             f"(attendu : {', '.join((*ADAPTATEURS, 'regles'))})")
        if fournisseur != "regles" and not env.get(p + "MODELE"):
            raise ValueError(f"{p}MODELE manquant")
        temp = env.get(p + "TEMPERATURE", "0")
        chaine.append(Maillon(
            nom=nom, fournisseur=fournisseur, modele=env.get(p + "MODELE", ""),
            cle=env.get(p + "CLE", ""), url=env.get(p + "URL", ""),
            delai_s=float(env.get(p + "DELAI_S") or delai_defaut),
            temperature=None if temp.lower() == "aucune" else float(temp),
            mode_json=env.get(p + "JSON") or None,
            prix_entree=_flottant(env.get(p + "PRIX_ENTREE")),
            prix_sortie=_flottant(env.get(p + "PRIX_SORTIE")),
            hebergeurs=tuple(h.strip() for h in env.get(p + "HEBERGEURS", "").split(",") if h.strip()),
            tri=env.get(p + "TRI") or None,
        ))
    return chaine


def charger_client(regles: Regles | None = None, env: Mapping[str, str] = os.environ) -> ClientLLM:
    return ClientLLM(lire_chaine(env), regles=regles)
