"""Client LLM multi-fournisseur (#9). Aucun appel réseau : fournisseurs simulés."""

import json
from dataclasses import replace

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


@pytest.mark.parametrize("raisonnement, attendu", [("non", {"thinkingBudget": 0}), (None, None)])
def test_gemini_reflexion_coupee_seulement_si_demande(raisonnement, attendu):  # revue de SAN sur #166
    # Gemini 2.5 Flash réfléchit par défaut (3 à 7 s par question) ; « non » la coupe, rien sinon
    m = replace(PRINCIPAL, raisonnement=raisonnement)
    t = transport(**{G: gemini_ok()})
    ClientLLM([m], transport=t).structurer("sys", "q", Capitale)
    assert json.loads(t.recues[0].content)["generationConfig"].get("thinkingConfig") == attendu


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


def test_openrouter_choix_et_tri_des_hebergeurs():
    m = Maillon(nom="or", fournisseur="openai_compatible", modele="openai/gpt-oss-120b", cle="o",
                url="https://openrouter.ai/api/v1", hebergeurs=("cerebras", "groq"), tri="latency")
    t = transport(**{O: openai_ok()})
    ClientLLM([m], transport=t).structurer("s", "q", Capitale)
    assert json.loads(t.recues[0].content)["provider"] == {
        "order": ["cerebras", "groq"], "sort": "latency", "require_parameters": True}


@pytest.mark.parametrize("valeur,attendu", [
    ("non", {"enabled": False}),
    ("low", {"effort": "low", "exclude": True}),
])
def test_openrouter_raisonnement_reglable(valeur, attendu):
    m = Maillon(nom="or", fournisseur="openai_compatible", modele="qwen/qwen3-32b", cle="o",
                url="https://openrouter.ai/api/v1", raisonnement=valeur)
    t = transport(**{O: openai_ok()})
    ClientLLM([m], transport=t).structurer("s", "q", Capitale)
    assert json.loads(t.recues[0].content)["reasoning"] == attendu


def test_raisonnement_absent_par_defaut():
    t = transport(**{O: openai_ok()})
    ClientLLM([OPENROUTER], transport=t).structurer("s", "q", Capitale)
    assert "reasoning" not in json.loads(t.recues[0].content)


def test_routage_d_hebergeurs_jamais_envoye_hors_openrouter():
    m = Maillon(nom="l", fournisseur="openai_compatible", modele="m", url="http://localhost:11434/v1",
                hebergeurs=("cerebras",))
    t = transport(localhost=openai_ok())
    ClientLLM([m], transport=t).structurer("s", "q", Capitale)
    assert "provider" not in json.loads(t.recues[0].content)


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


def test_delai_total_respecte_malgre_les_signaux_d_attente():
    """OpenRouter envoie des espaces pendant que le modèle travaille : le délai de
    httpx (par morceau) ne se déclenche jamais. Le chronomètre global, si."""
    import time

    def lent():
        for _ in range(40):  # 2 s de « signaux d'attente », un toutes les 50 ms
            time.sleep(0.05)
            yield b" "
        yield json.dumps(openai_ok()).encode()

    t = transport(**{O: lambda req: httpx.Response(200, content=lent()), A: anthropic_ok()})
    m = Maillon(nom="or", fournisseur="openai_compatible", modele="x", cle="o",
                url="https://openrouter.ai/api/v1", delai_s=0.3)
    debut = time.perf_counter()
    _, appel = ClientLLM([m, REPLI], transport=t).structurer("s", "q", Capitale)
    assert time.perf_counter() - debut < 1.0  # et non 2 s
    assert [x.statut for x in appel.tentatives] == ["delai", "ok"]
    assert "délai total" in appel.tentatives[0].detail


def _lent(secondes, reponse):
    """Fournisseur qui se tait `secondes` puis répond : ni octet ni signal d'attente entre-temps."""
    import time

    def gerer(req):
        time.sleep(secondes)
        return httpx.Response(200, json=reponse)
    return gerer


def test_delai_tenu_meme_quand_le_fournisseur_se_tait():
    """Recette du 08/10 : avec un délai de 3 s, un maillon pouvait durer 7,3 s (délai de lecture de httpx
    relancé après le dernier octet reçu). L'échéance est maintenant tenue à l'appel entier."""
    import time

    t = transport(**{G: _lent(1.5, gemini_ok()), A: anthropic_ok()})
    debut = time.perf_counter()
    _, appel = ClientLLM([replace(PRINCIPAL, delai_s=0.3), REPLI], transport=t).structurer("s", "q", Capitale)
    assert time.perf_counter() - debut < 0.8
    assert appel.maillon == "repli" and [x.statut for x in appel.tentatives] == ["delai", "ok"]
    assert appel.tentatives[0].latence_ms < 600


def test_relais_le_principal_garde_la_main_s_il_repond_dans_son_delai():
    """Relais : le repli part en parallèle au bout de 0,1 s ; le principal, meilleur, répond à 0,4 s,
    avant son délai : c'est sa réponse qui est servie."""
    t = transport(**{G: _lent(0.4, gemini_ok(json.dumps({"ville": "Dakar", "confiance": 0.9}))),
                     A: anthropic_ok(json.dumps({"ville": "Dakar", "confiance": 0.5}))})
    p = replace(PRINCIPAL, delai_s=1.0, relais_s=0.1)
    obj, appel = ClientLLM([p, REPLI], transport=t).structurer("s", "q", Capitale)
    assert obj.confiance == 0.9 and appel.maillon == "principal"
    assert {r.url.host for r in t.recues} == {G, A}  # le repli est bien parti en parallèle


def test_relais_le_repli_sert_des_l_echeance_du_principal():
    """Le principal dépasse son délai : la réponse du repli, déjà prête, part à l'échéance du principal,
    sans attendre un appel de plus (avant : délai du principal + durée du repli)."""
    import time

    t = transport(**{G: _lent(2.0, gemini_ok()), A: _lent(0.2, anthropic_ok())})
    p = replace(PRINCIPAL, delai_s=0.5, relais_s=0.1)
    debut = time.perf_counter()
    _, appel = ClientLLM([p, REPLI], transport=t).structurer("s", "q", Capitale)
    duree = time.perf_counter() - debut
    assert appel.maillon == "repli" and 0.45 < duree < 0.8
    assert [x.statut for x in appel.tentatives] == ["delai", "ok"]


def test_relais_pas_d_appel_inutile_quand_le_principal_est_rapide():
    t = transport(**{G: gemini_ok(), A: anthropic_ok()})
    _, appel = ClientLLM([replace(PRINCIPAL, relais_s=0.5), REPLI], transport=t).structurer("s", "q", Capitale)
    assert appel.maillon == "principal" and [r.url.host for r in t.recues] == [G]
    assert [x.maillon for x in appel.tentatives] == ["principal"]


def test_relais_le_repli_a_son_propre_delai():
    t = transport(**{G: _lent(2.0, gemini_ok()), A: _lent(2.0, anthropic_ok())})
    p, r = replace(PRINCIPAL, delai_s=0.4, relais_s=0.1), replace(REPLI, delai_s=0.4)
    with pytest.raises(EchecLLM) as e:
        ClientLLM([p, r, Maillon(nom="secours", fournisseur="regles")], transport=t).structurer("s", "q", Capitale)
    assert [x.statut for x in e.value.appel.tentatives] == ["delai", "delai", "indisponible"]
    assert e.value.appel.latence_ms < 800  # 0,1 + 0,4 s, pas 0,4 + 0,4 s


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
    "LLM_OR_FOURNISSEUR": "openai_compatible", "LLM_OR_MODELE": "openai/gpt-oss-120b",
    "LLM_OR_URL": "https://openrouter.ai/api/v1", "LLM_OR_HEBERGEURS": "cerebras, groq", "LLM_OR_TRI": "latency",
    "LLM_SECOURS_FOURNISSEUR": "regles",
    "LLM_HF_FOURNISSEUR": "huggingface", "LLM_HF_MODELE": "openai/gpt-oss-120b:fastest", "LLM_HF_CLE": "hf_x",
}


def test_changer_de_fournisseur_se_fait_dans_l_environnement():
    c = lire_chaine(ENV)
    assert [(m.nom, m.fournisseur) for m in c] == [("principal", "gemini"), ("repli", "anthropic"),
                                                   ("hf", "huggingface"), ("secours", "regles")]
    assert c[0].delai_s == 2 and c[1].delai_s == 3 and c[1].temperature is None
    assert c[0].relais_s is None  # sans LLM_<N>_RELAIS_S : chaîne séquentielle, comme avant
    assert lire_chaine({**ENV, "LLM_PRINCIPAL_RELAIS_S": "2.5"})[0].relais_s == 2.5
    assert lire_chaine({**ENV, "LLM_CHAINE": "or"})[0].hebergeurs == ("cerebras", "groq")
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
