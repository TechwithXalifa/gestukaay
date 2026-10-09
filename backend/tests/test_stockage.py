from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend.app import app
from gestukaay_backend.stockage import FiltreJournal, Stockage
from gestukaay_contracts.models import AskRequest, FeedbackRequest
from gestukaay_engine.fake import MoteurFactice

client = TestClient(app)


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


def test_admin_ferme_sans_compte(sans_compte):
    assert client.get("/admin/journal").status_code == 404


def test_admin_journal(connecter):
    client = TestClient(app)
    client.post("/v1/ask", json={"question": "Combien de personnes parlent sérère au Sénégal ?"})
    assert client.get("/admin/journal").status_code == 401
    client.cookies.set("gestukaay_admin", "faux", path="/admin")
    assert client.get("/admin/journal").status_code == 401
    connecter(client)
    r = client.get("/admin/journal", params={"issue": "aucune", "limite": 1})
    assert r.status_code == 200 and r.json()["total"] >= 1 and len(r.json()["lignes"]) == 1
    csv = client.get("/admin/journal.csv")
    assert csv.status_code == 200 and csv.content.decode("utf-16").startswith("recu_le\tcanal\t")


def test_suggestion_d_indicateur_depuis_un_refus():
    """EF-51 : la suggestion est gardée et visible dans le journal."""
    s = Stockage("")
    req = AskRequest(question="Combien de personnes parlent sérère au Sénégal ?")
    rep = MoteurFactice().repondre(req)
    s.enregistrer(rep, req)
    s.retour(FeedbackRequest(reponse_id=rep.reponse.id, type="suggestion_indicateur", commentaire=req.question))
    _, (ligne,) = s.journal(FiltreJournal())
    assert ligne["suggestions"] == 1
