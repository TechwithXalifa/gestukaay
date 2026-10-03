from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend.app import app
from gestukaay_backend.stockage import FiltreJournal, Stockage
from gestukaay_contracts.models import AskRequest, FeedbackRequest
from gestukaay_engine.fake import MoteurFactice

client = TestClient(app)
ADMIN = {"Authorization": "Bearer secret-de-test"}


def test_une_reponse_survit_au_redemarrage(tmp_path):
    url = f"sqlite:///{tmp_path / 'g.db'}"
    req = AskRequest(question="Combien d'habitants à Thiès ?")
    rep = MoteurFactice().repondre(req)
    Stockage(url).enregistrer(rep, req)
    relue = Stockage(url).lire(rep.reponse.id)  # nouvelle connexion, comme après un redémarrage
    assert relue is not None and relue.model_dump() == rep.model_dump()


def test_journal_sans_donnee_personnelle():
    s = Stockage("")
    req = AskRequest(question="Combien d'habitants à Thiès ?", canal="whatsapp", conversation_id="+221770000000")
    s.enregistrer(MoteurFactice().repondre(req), req)
    _, (ligne,) = s.journal(FiltreJournal())
    assert ligne["canal"] == "whatsapp" and ligne["issue"] == "exacte"
    assert ligne["conversation"] == s.hacher("+221770000000")
    assert "221" not in ligne["conversation"]


def test_journal_filtres_et_retours():
    s = Stockage("")
    for q in ("Combien d'habitants à Thiès ?", "Population de la ville de Thiès en 2023",
              "Combien de personnes parlent sérère au Sénégal ?"):
        req = AskRequest(question=q)
        s.enregistrer(MoteurFactice().repondre(req), req)
    total, lignes = s.journal(FiltreJournal(issue="aucune"))
    assert total == 1 and "sérère" in lignes[0]["question"]
    assert s.journal(FiltreJournal(texte="VILLE"))[0] == 1
    rid = lignes[0]["reponse_id"]
    s.retour(FeedbackRequest(reponse_id=rid, type="signalement", motif="autre"))
    s.retour(FeedbackRequest(reponse_id=rid, type="vote", vote="pas_utile"))
    _, (ligne,) = s.journal(FiltreJournal(issue="aucune"))
    assert ligne["vote"] == "pas_utile" and ligne["signalement"] == "autre"


def test_un_choix_confirme_garde_son_canal():
    r = client.post("/v1/ask", json={"question": "Population de la ville de Thiès en 2023", "canal": "telegram"})
    rid = r.json()["reponse"]["id"]
    nouvelle = client.post(f"/v1/ask/{rid}/confirm", json={"choix_id": "1"}).json()["reponse"]["id"]
    ligne = next(x for x in module_app.stockage.journal(FiltreJournal(limite=500))[1] if x["reponse_id"] == nouvelle)
    assert ligne["canal"] == "telegram" and ligne["confirme_depuis"] == rid


def test_admin_ferme_sans_jeton(monkeypatch):
    monkeypatch.delenv("GESTUKAAY_ADMIN_JETON", raising=False)
    assert client.get("/admin/journal", headers=ADMIN).status_code == 404


def test_admin_journal(monkeypatch):
    monkeypatch.setenv("GESTUKAAY_ADMIN_JETON", "secret-de-test")
    client.post("/v1/ask", json={"question": "Combien de personnes parlent sérère au Sénégal ?"})
    assert client.get("/admin/journal").status_code == 401
    assert client.get("/admin/journal", headers={"Authorization": "Bearer faux"}).status_code == 401
    r = client.get("/admin/journal", params={"issue": "aucune", "limite": 1}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["total"] >= 1 and len(r.json()["lignes"]) == 1
    csv = client.get("/admin/journal.csv", headers=ADMIN)
    assert csv.status_code == 200 and csv.text.startswith("﻿recu_le;canal;")
