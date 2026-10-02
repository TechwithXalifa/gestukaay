from fastapi.testclient import TestClient
from gestukaay_backend.app import app
from gestukaay_contracts.models import AskResponse

client = TestClient(app)


def _demander(question: str) -> dict:
    r = client.post("/v1/ask", json={"question": question})
    assert r.status_code == 200
    AskResponse.model_validate(r.json())  # conforme au contrat
    return r.json()["reponse"]


def test_trois_issues_de_bout_en_bout():
    assert _demander("Combien d'habitants à Thiès ?")["issue"] == "exacte"
    assert _demander("Population de la ville de Thiès en 2023")["issue"] == "approchee"
    assert _demander("Nombre de voitures à Kolda")["issue"] == "aucune"


def test_latence_et_relecture():
    rep = _demander("Combien d'habitants à Thiès ?")
    assert rep["latence_ms"] is not None
    assert rep["url"].endswith(f"/r/{rep['id']}") and "gestukaay.test" not in rep["url"]
    assert client.get(f"/v1/answers/{rep['id']}").json()["reponse"]["id"] == rep["id"]


def test_confirmer_une_approchee():
    rep = _demander("Population de la ville de Thiès en 2023")
    r = client.post(f"/v1/ask/{rep['id']}/confirm", json={"choix_id": "1"})
    assert r.status_code == 200 and r.json()["reponse"]["issue"] == "exacte"


def test_erreurs_au_format_problem():
    r = client.get("/v1/answers/inconnue")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    rep = _demander("Combien d'habitants à Thiès ?")
    assert client.post(f"/v1/ask/{rep['id']}/confirm", json={"choix_id": "1"}).status_code == 409


def test_question_trop_courte_refusee():
    assert client.post("/v1/ask", json={"question": "a"}).status_code == 422


def test_feedback():
    rep = _demander("Combien d'habitants à Thiès ?")
    r = client.post("/v1/feedback", json={"reponse_id": rep["id"], "type": "vote", "vote": "utile"})
    assert r.status_code == 204
