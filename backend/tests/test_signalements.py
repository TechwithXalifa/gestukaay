"""Relecture des signalements et des suggestions d'indicateur (back-office)."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app


def _signaler(client, question: str, **retour) -> str:
    rid = client.post("/v1/ask", json={"question": question}).json()["reponse"]["id"]
    assert client.post("/v1/feedback", json={"reponse_id": rid, **retour}).status_code == 204
    return rid


def test_a_traiter_puis_corrige_avec_note(connecter, base_admin):
    client = TestClient(module_app.app)
    rid = _signaler(client, "Combien d'habitants à Thiès ?", type="signalement", motif="chiffre_faux",
                    commentaire="Le recensement dit autre chose")
    _signaler(client, "Combien de personnes parlent sérère ?", type="suggestion_indicateur", commentaire="langues")
    _signaler(client, "Combien d'habitants à Thiès ?", type="vote", vote="utile")  # un vote n'est pas à relire
    assert client.get("/admin/signalements").status_code == 401
    connecter(client)

    r = client.get("/admin/signalements").json()
    assert r["comptes"] == {"a_traiter": 2, "en_cours": 0, "corrige": 0, "rejete": 0}
    s = next(x for x in r["lignes"] if x["type"] == "signalement")
    assert s["question"] == "Combien d'habitants à Thiès ?" and s["motif"] == "chiffre_faux" and s["statut"] == "a_traiter"
    assert sum(x["recus"] for x in r["par_semaine"]) == 2 and len(r["par_semaine"]) == 8

    corps = {"reponse_id": rid, "recu_le": s["recu_le"], "type": "signalement", "statut": "corrige",
             "note": "Corrigé par #261"}
    assert client.post("/admin/signalements/suivi", json=corps).status_code == 204
    r = client.get("/admin/signalements", params={"statut": "corrige"}).json()
    [corrige] = r["lignes"]
    assert corrige["note"] == "Corrigé par #261" and corrige["par"] == "SAN" and r["comptes"]["a_traiter"] == 1
    # Un second changement remplace le premier, il ne s'ajoute pas
    client.post("/admin/signalements/suivi", json={**corps, "statut": "rejete", "note": ""})
    r = client.get("/admin/signalements").json()
    assert r["comptes"]["rejete"] == 1 and r["comptes"]["corrige"] == 0
    assert next(x for x in r["lignes"] if x["statut"] == "rejete")["note"] is None


def test_filtres_et_erreurs(connecter, base_admin):
    client = TestClient(module_app.app)
    _signaler(client, "Combien de personnes parlent sérère ?", type="suggestion_indicateur", commentaire="langues")
    connecter(client)
    assert client.get("/admin/signalements", params={"type": "signalement"}).json()["lignes"] == []
    assert len(client.get("/admin/signalements", params={"type": "suggestion_indicateur"}).json()["lignes"]) == 1
    assert client.get("/admin/signalements", params={"jours": 12}).status_code == 422
    inconnu = {"reponse_id": "x", "recu_le": "2026-01-01T00:00:00+00:00", "type": "signalement", "statut": "corrige"}
    assert client.post("/admin/signalements/suivi", json=inconnu).status_code == 404
    assert client.post("/admin/signalements/suivi", json={**inconnu, "statut": "perdu"}).status_code == 422
