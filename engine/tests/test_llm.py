"""Client LLM multi-fournisseur (#9). Aucun appel réseau : fournisseurs simulés."""

import json

import httpx
import pytest
from gestukaay_contracts.models import RequeteStructuree
from gestukaay_engine.llm import ClientLLM, EchecLLM, Maillon, lire_chaine
from gestukaay_engine.llm.adaptateurs import schema_pour_anthropic
from pydantic import BaseModel, ConfigDict, Field


class Capitale(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ville: str
    confiance: float = Field(ge=0, le=1)


BON = {"ville": "Dakar", "confiance": 0.9}
BON_JSON = json.dumps(BON)


def openai_ok(texte=BON_JSON, cout=0.0001):
    return {"model": "x/modele", "choices": [{"message": {"content": texte}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 10, "cost": cout}}


def anthropic_ok(texte=BON_JSON):
    return {"model": "claude-haiku-4-5", "stop_reason": "end_turn", "content": [{"type": "text", "text": texte}],
            "usage": {"input_tokens": 100, "output_tokens": 20}}


def gemini_ok(texte=BON_JSON):
    return {"modelVersion": "gemini-2.5-flash", "candidates": [{"content": {"parts": [{"text": texte}]},
            "finishReason": "STOP"}], "usageMetadata": {"promptTokenCount": 90, "candidatesTokenCount": 15}}


def transport(**par_hote):
    """par_hote : {"openrouter.ai": réponse | Exception | callable(request)}."""
    recues = []

    def gerer(request: httpx.Request):
        recues.append(request)
        r = par_hote[request.url.host]
        if callable(r):
            r = r(request)
        if isinstance(r, Exception):
            raise r
        if isinstance(r, httpx.Response):
            return r
        return httpx.Response(200, json=r)

    t = httpx.MockTransport(gerer)
    t.recues = recues
    return t


PRINCIPAL = Maillon(nom="principal", fournisseur="gemini", modele="gemini-2.5-flash", cle="g",
                    prix_entree=0.30, prix_sortie=2.50)
REPLI = Maillon(nom="repli", fournisseur="anthropic", modele="claude-haiku-4-5", cle="a")
OPENROUTER = Maillon(nom="or", fournisseur="openai_compatible", modele="google/gemini-2.5-flash", cle="o",
                     url="https://openrouter.ai/api/v1")
G, A, O = "generativelanguage.googleapis.com", "api.anthropic.com", "openrouter.ai"


# ---- chaque adaptateur, cas nominal -------------------------------------------------

def test_gemini_direct_et_cout_calcule_depuis_les_prix():
    t = transport(**{G: gemini_ok()})
    obj, appel = ClientLLM([PRINCIPAL], transport=t).structurer("sys", "Capitale ?", Capitale)
    assert obj.ville == "Dakar" and appel.maillon == "principal"
    assert appel.cout_usd == pytest.approx((90 * 0.30 + 15 * 2.50) / 1e6)
    req = t.recues[0]
    assert req.url.path == "/v1beta/models/gemini-2.5-flash:generateContent"
    assert req.headers["x-goog-api-key"] == "g"
    corps = json.loads(req.content)
    assert corps["generationConfig"] == {"responseMimeType": "application/json", "temperature": 0.0}


def test_anthropic_direct_avec_sortie_structuree_native():
    t = transport(**{A: anthropic_ok()})
    obj, appel = ClientLLM([REPLI], transport=t).structurer("sys", "q", Capitale)
    assert obj.ville == "Dakar" and appel.jetons_entree == 100 and appel.cout_usd is None
    req = t.recues[0]
    assert req.headers["x-api-key"] == "a" and req.headers["anthropic-version"] == "2023-06-01"
    schema = json.loads(req.content)["output_config"]["format"]["schema"]
    assert "minimum" not in json.dumps(schema)  # contraintes retirées, revérifiées chez nous


def test_openrouter_cout_exact_fourni_par_le_fournisseur():
    t = transport(**{O: openai_ok(cout=0.00042)})
    _, appel = ClientLLM([OPENROUTER], transport=t).structurer("sys", "q", Capitale)
    assert appel.cout_usd == 0.00042
    corps = json.loads(t.recues[0].content)
    assert corps["usage"] == {"include": True} and corps["response_format"] == {"type": "json_object"}
    assert t.recues[0].headers["authorization"] == "Bearer o"


def test_ollama_local_meme_adaptateur_sans_cle():
    local = Maillon(nom="local", fournisseur="openai_compatible", modele="qwen3:4b",
                    url="http://localhost:11434/v1")
    t = transport(localhost=openai_ok())
    obj, _ = ClientLLM([local], transport=t).structurer("sys", "q", Capitale)
    assert obj.ville == "Dakar" and "authorization" not in t.recues[0].headers


def test_huggingface_routeur_par_defaut_et_consigne_json():
    hf = Maillon(nom="hf", fournisseur="huggingface", modele="openai/gpt-oss-120b:cheapest", cle="hf_x",
                 prix_entree=0.1, prix_sortie=0.5)
    t = transport(**{"router.huggingface.co": openai_ok(cout=None)})
    obj, appel = ClientLLM([hf], transport=t).structurer("sys", "q", Capitale)
    req = t.recues[0]
    assert str(req.url) == "https://router.huggingface.co/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer hf_x"
    corps = json.loads(req.content)
    assert corps["model"] == "openai/gpt-oss-120b:cheapest"  # le suffixe choisit l'hébergeur
    assert "response_format" not in corps and "schéma JSON" in corps["messages"][0]["content"]
    assert obj.ville == "Dakar" and appel.cout_usd == pytest.approx((120 * 0.1 + 10 * 0.5) / 1e6)


def test_huggingface_endpoint_dedie_et_mode_json_configurable():
    hf = Maillon(nom="hf", fournisseur="huggingface", modele="tgi", cle="hf_x",
                 url="https://mon-endpoint.endpoints.huggingface.cloud/v1", mode_json="objet")
    t = transport(**{"mon-endpoint.endpoints.huggingface.cloud": openai_ok()})
    ClientLLM([hf], transport=t).structurer("sys", "q", Capitale)
    assert json.loads(t.recues[0].content)["response_format"] == {"type": "json_object"}


# ---- la chaîne de secours ----------------------------------------------------------

@pytest.mark.parametrize(
    "panne,statut",
    [
        (httpx.ReadTimeout("trop long"), "delai"),
        (httpx.ConnectError("pas de réseau"), "reseau"),
        (httpx.Response(503, text="surcharge"), "http"),
        ({"candidates": [{"finishReason": "SAFETY", "content": {"parts": []}}]}, "refus"),
        (gemini_ok("Bien sûr ! La capitale est Dakar."), "json"),
        (gemini_ok(json.dumps({"ville": "Dakar", "confiance": 7})), "schema"),
    ],
)
def test_le_principal_echoue_le_repli_repond(panne, statut):
    t = transport(**{G: panne, A: anthropic_ok()})
    obj, appel = ClientLLM([PRINCIPAL, REPLI], transport=t).structurer("sys", "q", Capitale)
    assert obj.ville == "Dakar" and appel.maillon == "repli"
    assert [(x.maillon, x.statut) for x in appel.tentatives] == [("principal", statut), ("repli", "ok")]


def test_anthropic_refus_passe_au_suivant():
    refus = {"stop_reason": "refusal", "stop_details": {"category": "cyber"}, "content": []}
    t = transport(**{A: refus, O: openai_ok()})
    _, appel = ClientLLM([REPLI, OPENROUTER], transport=t).structurer("s", "q", Capitale)
    assert [x.statut for x in appel.tentatives] == ["refus", "ok"]


def test_regles_locales_en_dernier_recours_sans_reseau():
    t = transport(**{G: httpx.ConnectError("x"), A: httpx.ConnectError("x")})
    regles = Maillon(nom="secours", fournisseur="regles")
    client = ClientLLM([PRINCIPAL, REPLI, regles], regles=lambda s, u: {"ville": "Dakar", "confiance": 0.4},
                       transport=t)
    obj, appel = client.structurer("s", "q", Capitale)
    assert obj.confiance == 0.4 and appel.maillon == "secours" and appel.modele == "regles"


def test_tout_echoue_echecllm_avec_le_detail_de_chaque_essai():
    t = transport(**{G: httpx.ReadTimeout("x"), A: httpx.Response(500)})
    with pytest.raises(EchecLLM) as e:
        ClientLLM([PRINCIPAL, REPLI, Maillon(nom="secours", fournisseur="regles")],
                  transport=t).structurer("s", "q", Capitale)
    assert [x.statut for x in e.value.appel.tentatives] == ["delai", "http", "indisponible"]


def test_cle_absente_indisponible_sans_appel_reseau():
    t = transport(**{O: openai_ok()})
    sans_cle = Maillon(nom="principal", fournisseur="gemini", modele="gemini-2.5-flash")
    _, appel = ClientLLM([sans_cle, OPENROUTER], transport=t).structurer("s", "q", Capitale)
    assert appel.tentatives[0].statut == "indisponible" and "LLM_PRINCIPAL_CLE" in appel.tentatives[0].detail
    assert [r.url.host for r in t.recues] == [O]  # Gemini n'a pas été appelé


def test_message_d_erreur_lisible():
    t = transport(**{A: httpx.Response(401, json={"type": "error", "error": {
        "type": "authentication_error", "message": "invalid x-api-key"}})})
    with pytest.raises(EchecLLM) as e:
        ClientLLM([REPLI], transport=t).structurer("s", "q", Capitale)
    assert e.value.appel.tentatives[0].detail == "401 invalid x-api-key"


def test_json_entoure_d_un_bloc_de_code_accepte():
    t = transport(**{O: openai_ok("```json\n" + json.dumps(BON) + "\n```")})
    obj, _ = ClientLLM([OPENROUTER], transport=t).structurer("s", "q", Capitale)
    assert obj.ville == "Dakar"


def test_temperature_non_envoyee_si_aucune():
    m = Maillon(nom="p", fournisseur="anthropic", modele="claude-sonnet-5-5", cle="a", temperature=None)
    t = transport(**{A: anthropic_ok()})
    ClientLLM([m], transport=t).structurer("s", "q", Capitale)
    assert "temperature" not in json.loads(t.recues[0].content)


# ---- schéma pour Anthropic -----------------------------------------------------------

def test_schema_requete_structuree_a_cles_libres_bascule_en_consigne():
    # desagregation est un dict[str, str] : non exprimable en sortie structurée Anthropic
    assert schema_pour_anthropic(RequeteStructuree.model_json_schema()) is None
    t = transport(**{A: anthropic_ok(json.dumps({"intention": "valeur", "confiance": 0.9}))})
    obj, _ = ClientLLM([REPLI], transport=t).structurer("sys", "q", RequeteStructuree)
    corps = json.loads(t.recues[0].content)
    assert "output_config" not in corps and "schéma JSON" in corps["system"]
    assert obj.intention == "valeur"


# ---- configuration -------------------------------------------------------------------

ENV = {
    "LLM_CHAINE": "principal, repli ,hf,secours",
    "LLM_PRINCIPAL_FOURNISSEUR": "gemini", "LLM_PRINCIPAL_MODELE": "gemini-2.5-flash",
    "LLM_PRINCIPAL_CLE": "g", "LLM_PRINCIPAL_PRIX_ENTREE": "0.3", "LLM_PRINCIPAL_PRIX_SORTIE": "2.5",
    "LLM_REPLI_FOURNISSEUR": "anthropic", "LLM_REPLI_MODELE": "claude-haiku-4-5", "LLM_REPLI_CLE": "a",
    "LLM_REPLI_DELAI_S": "3", "LLM_REPLI_TEMPERATURE": "aucune",
    "LLM_SECOURS_FOURNISSEUR": "regles",
    "LLM_HF_FOURNISSEUR": "huggingface", "LLM_HF_MODELE": "openai/gpt-oss-120b:fastest", "LLM_HF_CLE": "hf_x",
}


def test_changer_de_fournisseur_se_fait_dans_l_environnement():
    c = lire_chaine(ENV)
    assert [(m.nom, m.fournisseur) for m in c] == [("principal", "gemini"), ("repli", "anthropic"),
                                                   ("hf", "huggingface"), ("secours", "regles")]
    assert c[0].delai_s == 2 and c[1].delai_s == 3 and c[1].temperature is None
    tout_openrouter = {**ENV, "LLM_PRINCIPAL_FOURNISSEUR": "openai_compatible",
                       "LLM_PRINCIPAL_URL": "https://openrouter.ai/api/v1",
                       "LLM_PRINCIPAL_MODELE": "google/gemini-2.5-flash"}
    assert lire_chaine(tout_openrouter)[0].fournisseur == "openai_compatible"


@pytest.mark.parametrize("env,message", [
    ({"LLM_CHAINE": "p", "LLM_P_FOURNISSEUR": "chatgpt"}, "FOURNISSEUR invalide"),
    ({"LLM_CHAINE": "p", "LLM_P_FOURNISSEUR": "gemini"}, "MODELE manquant"),
])
def test_configuration_invalide_explique_l_erreur(env, message):
    with pytest.raises(ValueError, match=message):
        lire_chaine(env)


def test_chaine_vide_refusee():
    with pytest.raises(ValueError, match="LLM_CHAINE"):
        ClientLLM([])
