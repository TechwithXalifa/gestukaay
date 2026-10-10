"""Rejouer une question du journal sur le moteur actuel (back-office), sans rien enregistrer."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app


def test_rejouer_sans_enregistrer(connecter, base_admin):
    client = TestClient(module_app.app)
    rid = client.post("/v1/ask", json={"question": "Combien d'habitants à Thiès ?"}).json()["reponse"]["id"]
    assert client.post("/admin/rejouer", json={"reponse_id": rid}).status_code == 401
    connecter(client)
    total = client.get("/admin/journal").json()["total"]
    r = client.post("/admin/rejouer", json={"reponse_id": rid}).json()
    assert r["question"] == "Combien d'habitants à Thiès ?" and r["identique"] is True
    assert r["avant"]["issue"] == r["apres"]["issue"] == "exacte"
    assert any("Thiès" in t for t in r["apres"]["texte"]) and r["apres"]["latence_ms"] >= 0
    assert client.get("/admin/journal").json()["total"] == total  # ni réponse ni ligne de journal en plus


def test_rejouer_un_refus_et_une_reponse_inconnue(connecter, base_admin):
    client = TestClient(module_app.app)
    rid = client.post("/v1/ask", json={"question": "Combien de personnes parlent sérère ?"}).json()["reponse"]["id"]
    connecter(client)
    r = client.post("/admin/rejouer", json={"reponse_id": rid}).json()
    assert r["apres"]["issue"] == "aucune" and r["apres"]["motif"] == "hors_socle"
    assert client.post("/admin/rejouer", json={"reponse_id": "inconnue"}).status_code == 404


def test_un_changement_se_voit(connecter, base_admin, monkeypatch):
    client = TestClient(module_app.app)
    rid = client.post("/v1/ask", json={"question": "Combien d'habitants à Thiès ?"}).json()["reponse"]["id"]
    connecter(client)
    # Le moteur a changé entre-temps : la même question part maintenant en refus
    refus = module_app.moteur.repondre
    monkeypatch.setattr(module_app.moteur, "repondre",
                        lambda req, ctx=None: refus(req.model_copy(update={"question": "sérère ?"}), ctx))
    r = client.post("/admin/rejouer", json={"reponse_id": rid}).json()
    assert r["identique"] is False and r["avant"]["issue"] == "exacte" and r["apres"]["issue"] == "aucune"
