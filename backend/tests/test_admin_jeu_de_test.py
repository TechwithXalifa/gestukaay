"""Jeu de test dans le back-office (cahier 5.10) : lancer le benchmark de KBD, garder, comparer."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend import jeu_de_test
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.moteur import MoteurReel
from gestukaay_engine.socle import Observation, Socle, SourceJeu

client = TestClient(module_app.app)
N = len(jeu_de_test.questions())  # taille du jeu de test : elle évolue (104 depuis la 0024)


def _socle() -> Socle:
    """Petit socle synthétique : le benchmark tourne en entier, la plupart des questions échouent."""
    obs = [Observation(id=f"p-{z}", indicateur="pvswjnd", zone=z, zone_presumee=False, periode="2023",
                       desagregation=(("age", "Total"), ("sexe", "Total")), valeur=v, unite="", echelle="1",
                       source_id="pvswjnd", nature="observee", base_projection="")
           for z, v in (("SN", 18126390), ("SN-TH", 2463677), ("SN-DK", 4004426))]
    sources = {"pvswjnd": SourceJeu("pvswjnd", "ANSD", "ANSD", "RGPH-5", date(2023, 10, 31), "", "https://x/pvswjnd")}
    return Socle(obs, sources, "test")


@pytest.fixture
def admin(monkeypatch, connecter):
    connecter(client)
    monkeypatch.setattr(module_app, "executer_benchmark", lambda tache: tache())  # synchrone


@pytest.fixture
def reel(monkeypatch, admin):
    monkeypatch.setattr(module_app, "moteur", MoteurReel(_socle(), Comprehension(None)))


def test_ferme_sans_compte(sans_compte):
    assert client.get("/admin/jeu-de-test").status_code == 404


def test_faux_moteur_pas_de_benchmark(admin):
    r = client.get("/admin/jeu-de-test").json()
    assert r["disponible"] is False and len(r["questions"]) == N
    assert set(r["questions"][0]) == {"id", "question", "type", "langue", "issue_attendue"}
    assert client.post("/admin/jeu-de-test/executions", json={"mode": "regles"}).status_code == 503


def test_lancer_garder_et_relire(reel):
    assert client.post("/admin/jeu-de-test/executions", json={"mode": "autre"}).status_code == 422
    r = client.post("/admin/jeu-de-test/executions", json={"mode": "regles"})
    assert r.status_code == 202
    eid = r.json()["id"]
    liste = client.get("/admin/jeu-de-test").json()
    assert liste["disponible"] is True
    execution = next(e for e in liste["executions"] if e["id"] == eid)
    assert execution["statut"] == "terminee" and execution["mode"] == "regles"
    assert execution["resume"]["nb_total"] == N and execution["resume"]["nb_violations_invariant"] == 0
    detail = client.get(f"/admin/jeu-de-test/executions/{eid}").json()
    evaluations = detail["resultat"]["evaluations"]
    assert len(evaluations) == N and {"question_id", "issue_obtenue", "reponse_correcte"} <= set(evaluations[0])
    assert client.get("/admin/jeu-de-test/executions/inconnue").status_code == 404


def test_une_seule_execution_a_la_fois(reel):
    assert jeu_de_test._verrou.acquire(blocking=False)
    try:
        assert client.post("/admin/jeu-de-test/executions", json={"mode": "regles"}).status_code == 409
    finally:
        jeu_de_test._verrou.release()


def test_un_echec_est_garde(reel, monkeypatch):
    def panne(*a, **k):
        raise RuntimeError("socle indisponible")

    monkeypatch.setattr(jeu_de_test.benchmark(), "executer_benchmark", panne)
    eid = client.post("/admin/jeu-de-test/executions", json={"mode": "regles"}).json()["id"]
    execution = next(e for e in client.get("/admin/jeu-de-test").json()["executions"] if e["id"] == eid)
    assert execution["statut"] == "echec" and "socle indisponible" in execution["erreur"]
    assert jeu_de_test._verrou.acquire(blocking=False)  # le verrou est bien rendu
    jeu_de_test._verrou.release()


def test_mode_llm_desactive_par_defaut(reel, monkeypatch):
    """Aucune dépense sans accord : sans GESTUKAAY_BENCHMARK_LLM=oui, le mode LLM répond 403."""
    monkeypatch.delenv("GESTUKAAY_BENCHMARK_LLM", raising=False)
    assert client.get("/admin/jeu-de-test").json()["llm_autorise"] is False
    r = client.post("/admin/jeu-de-test/executions", json={"mode": "llm"})
    assert r.status_code == 403 and r.json()["title"] == "Désactivé sur ce serveur"
    monkeypatch.setenv("GESTUKAAY_BENCHMARK_LLM", "oui")
    assert client.get("/admin/jeu-de-test").json()["llm_autorise"] is True
