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
    assert ligne["vote"] == "pas_utile" and ligne["signalement"] == "autre" and ligne["commentaire"] is None


def test_journal_commentaire_et_filtre_retour():
    """Le commentaire de l'usager est lisible au journal, et le filtre « Retour » isole les réponses signalées."""
    s = Stockage("")
    rids = []
    for q in ("Combien d'habitants à Thiès ?", "Quel est le taux de pauvreté à Kolda ?",
              "Combien de personnes parlent sérère au Sénégal ?"):
        req = AskRequest(question=q)
        rep = MoteurFactice().repondre(req)
        s.enregistrer(rep, req)
        rids.append(rep.reponse.id)
    s.retour(FeedbackRequest(reponse_id=rids[0], type="signalement", motif="chiffre_faux",
                             commentaire="Le RGPH-5 donne un autre chiffre"))
    s.retour(FeedbackRequest(reponse_id=rids[1], type="vote", vote="utile"))
    s.retour(FeedbackRequest(reponse_id=rids[2], type="suggestion_indicateur", commentaire="Langues parlées"))
    total, (ligne,) = s.journal(FiltreJournal(retour="signale"))
    assert total == 1 and ligne["reponse_id"] == rids[0]
    assert ligne["signalement"] == "chiffre_faux" and ligne["commentaire"] == "Le RGPH-5 donne un autre chiffre"
    assert [x["reponse_id"] for x in s.journal(FiltreJournal(retour="utile"))[1]] == [rids[1]]
    assert s.journal(FiltreJournal(retour="pas_utile"))[0] == 0
    _, (ligne,) = s.journal(FiltreJournal(retour="suggere"))
    assert ligne["suggestions"] == 1 and ligne["suggestion"] == "Langues parlées"


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
    assert "commentaire" in csv.content.decode("utf-16").splitlines()[0]
    assert client.get("/admin/journal", params={"retour": "signale"}).status_code == 200
    assert client.get("/admin/journal", params={"retour": "nimporte"}).status_code == 422


def test_journal_csv_sans_formule(connecter):
    """Un commentaire d'usager qui commence par « = » reste du texte dans le tableur (injection CSV)."""
    client = TestClient(app)
    rid = client.post("/v1/ask", json={"question": "Combien d'habitants à Thiès ?"}).json()["reponse"]["id"]
    client.post("/v1/feedback", json={"reponse_id": rid, "type": "signalement", "motif": "autre",
                                      "commentaire": '=HYPERLINK("http://x","clic")'})
    connecter(client)
    texte = client.get("/admin/journal.csv", params={"retour": "signale"}).text
    assert "'=HYPERLINK" in texte and '\t=HYPERLINK' not in texte and '\t"=HYPERLINK' not in texte


def test_suggestion_d_indicateur_depuis_un_refus():
    """EF-51 : la suggestion est gardée et visible dans le journal."""
    s = Stockage("")
    req = AskRequest(question="Combien de personnes parlent sérère au Sénégal ?")
    rep = MoteurFactice().repondre(req)
    s.enregistrer(rep, req)
    s.retour(FeedbackRequest(reponse_id=rep.reponse.id, type="suggestion_indicateur", commentaire=req.question))
    _, (ligne,) = s.journal(FiltreJournal())
    assert ligne["suggestions"] == 1



def test_sel_garde_d_un_demarrage_a_l_autre(tmp_path, monkeypatch):
    """Audit du 09/10 : sans GESTUKAAY_SEL, le sel était tiré à chaque démarrage et la conversation (suivi,
    « 1 » de WhatsApp) était perdue. Il est maintenant gardé dans la base."""
    monkeypatch.delenv("GESTUKAAY_SEL", raising=False)
    url = f"sqlite:///{tmp_path / 'g.db'}"
    assert Stockage(url).hacher("whatsapp:+221770000000") == Stockage(url).hacher("whatsapp:+221770000000")
    monkeypatch.setenv("GESTUKAAY_SEL", "sel-de-preprod")
    assert Stockage(url).hacher("x") == Stockage("").hacher("x")  # la variable prime sur la base


def test_sel_de_la_base_signale(tmp_path, monkeypatch, caplog):
    """Revue de KBD sur #200 : un sel gardé dans la base est signalé au démarrage ; pas en mémoire ni avec la variable."""
    monkeypatch.delenv("GESTUKAAY_SEL", raising=False)
    Stockage(f"sqlite:///{tmp_path / 'g.db'}")
    assert "GESTUKAAY_SEL absent" in caplog.text
    caplog.clear()
    Stockage("")
    monkeypatch.setenv("GESTUKAAY_SEL", "sel-de-preprod")
    Stockage(f"sqlite:///{tmp_path / 'g.db'}")
    assert "GESTUKAAY_SEL absent" not in caplog.text


def test_base_en_memoire_signalee(tmp_path, caplog):
    """Sans GESTUKAAY_BASE, la base est en mémoire : les liens /r/… cassent au redémarrage (09/10). C'est dit
    au démarrage ; pas avec un fichier SQLite."""
    Stockage("")
    assert "GESTUKAAY_BASE vide" in caplog.text
    caplog.clear()
    Stockage("sqlite:///:memory:")
    assert "GESTUKAAY_BASE vide" in caplog.text
    caplog.clear()
    Stockage(f"sqlite:///{tmp_path / 'g.db'}")
    assert "GESTUKAAY_BASE vide" not in caplog.text
