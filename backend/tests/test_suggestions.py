"""Autocomplétion de la question (EF-10), sur le faux moteur : questions types et catalogue."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend import securite
from gestukaay_backend.suggestions import QUESTIONS_TYPES, SuggestionsResponse

client = TestClient(module_app.app)


def textes(q: str) -> list[str]:
    r = client.get("/v1/suggestions", params={"q": q})
    assert r.status_code == 200
    return [s.texte for s in SuggestionsResponse.model_validate(r.json()).suggestions]


def test_trop_court_ou_trop_long():
    assert textes("") == [] and textes("p") == []
    assert client.get("/v1/suggestions", params={"q": "x" * 101}).status_code == 422


def test_question_type_puis_catalogue_sans_doublon():
    s = textes("pauv")
    assert s[0] == "Quel est le taux de pauvreté au Sénégal ?"
    # Le catalogue ne repropose pas l'indicateur déjà servi par la question type
    assert "Taux de pauvreté" not in s


def test_zone_commencee_et_zone_seule():
    assert textes("pauvreté à kol")[0] == "Quel est le taux de pauvreté à Kolda ?"
    seule = textes("kolda")
    assert "Combien d'habitants à Kolda ?" in seule and all("à Kolda" in t for t in seule)
    # Après d'autres mots, deux lettres suffisent ; un département garde les questions qui s'y posent
    assert textes("combien d'habitants à mbo") == ["Combien d'habitants à Mbour ?"]
    assert textes("chômage th")[0] == "Quel est le taux de chômage à Thiès ?"
    # Seules, deux lettres restent un début de mot ; un mot outil n'est jamais un lieu (« ou » : pas Oussouye)
    assert textes("pi") == ["Quel est le PIB du Sénégal ?"]  # pas Pikine
    assert textes("chômage ou")[0] == "Quel est le taux de chômage au Sénégal ?"


def test_catalogue_au_niveau_de_la_zone():
    s = client.get("/v1/suggestions", params={"q": "consommation thi"}).json()["suggestions"]
    assert s == [{"texte": "Consommation moyenne par tête à Thiès",
                  "indicateur": {"code": "jcvcajc.total", "libelle": "Consommation moyenne par tête"}}]


def test_questions_types_bien_formees():
    for qt in QUESTIONS_TYPES:
        assert qt.gabarit.endswith(" ?") and qt.mots and qt.code
        assert ("{zone}" in qt.gabarit) == bool(qt.defaut)  # sans zone tapée : le défaut la remplace


def test_limite_de_requetes_large():
    assert securite.groupe("/v1/suggestions") == "suggestions"
    assert securite.LIMITES["suggestions"] >= securite.LIMITES["explorer"]
