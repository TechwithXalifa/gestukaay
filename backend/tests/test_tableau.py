"""Tableau de bord du back-office (US-28, maquette BO-Tableau)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend.stockage import Stockage
from gestukaay_contracts.models import AskRequest, FeedbackRequest
from gestukaay_engine.fake import MoteurFactice

MOTEUR = MoteurFactice()


def _poser(st: Stockage, question: str, latence: int, langue="auto", canal="web"):
    req = AskRequest(question=question, langue=langue, canal=canal)
    rep = MOTEUR.repondre(req)
    rep.reponse.latence_ms = latence
    st.enregistrer(rep, req)
    return rep.reponse


def test_indicateurs_de_qualite():
    st = Stockage("")
    exacte = _poser(st, "Combien d'habitants à Thiès ?", 1000)
    _poser(st, "Ñaata nit ñoo dëkk Tiés ?", 3000, langue="wo", canal="whatsapp")
    _poser(st, "Population de la ville de Thiès en 2023", 2000)
    for _ in range(2):
        _poser(st, "Combien de personnes parlent sérère au Sénégal ?", 4000)
    _poser(st, "blabla", 500)
    st.retour(FeedbackRequest(reponse_id=exacte.id, type="vote", vote="pas_utile"))
    st.retour(FeedbackRequest(reponse_id=exacte.id, type="vote", vote="utile"))  # le dernier vote compte
    st.retour(FeedbackRequest(reponse_id=exacte.id, type="signalement", motif="chiffre_faux"))

    t = st.tableau(30)
    assert t["questions"] == 6 and t["questions_periode_precedente"] == 0
    assert t["issues"] == {"exacte": 2, "approchee": 1, "aucune": 3}
    assert t["latence_mediane_ms"] == 2500 and t["latence_p95_ms"] == 4000
    assert t["part_wolof"] == round(1 / 6, 3)
    assert (t["votes"], t["satisfaction"], t["signalements"]) == (1, 1.0, 1)
    assert len(t["par_jour"]) == 30 and t["par_jour"][-1]["questions"] == 6
    assert t["non_resolues"][0] == {"question": "Combien de personnes parlent sérère au Sénégal ?", "langue": "fr",
                                    "motif": "hors_socle", "occurrences": 2}
    assert st.tableau(30, canal="whatsapp")["questions"] == 1
    assert st.tableau(30, langue="wo")["part_wolof"] == 1.0


def test_salutations_ni_refus_ni_non_resolues():
    # 0033 : « Bonjour » reçoit une réponse polie (motif conversation), ce n'est pas un échec du moteur
    st = Stockage("")
    _poser(st, "Combien d'habitants à Thiès ?", 1000)
    _poser(st, "Combien de personnes parlent sérère au Sénégal ?", 1000)
    for i in range(3):  # le faux moteur n'a pas de motif conversation : un refus relabellisé
        rep = MOTEUR.repondre(AskRequest(question="Combien de personnes parlent sérère au Sénégal ?"))
        rep.reponse.motif, rep.reponse.question, rep.reponse.id = "conversation", "Bonjour", f"conv{i}"
        st.enregistrer(rep, AskRequest(question="Bonjour"))
    t = st.tableau(30)
    assert t["questions"] == 5 and t["conversations"] == 3
    assert t["issues"] == {"exacte": 1, "approchee": 0, "aucune": 1}
    assert [g["question"] for g in t["non_resolues"]] == ["Combien de personnes parlent sérère au Sénégal ?"]


def test_periode_et_confirmations():
    st = Stockage("")
    approchee = _poser(st, "Population de la ville de Thiès en 2023", 2000)
    st.enregistrer(MOTEUR.executer(approchee.choix[0].requete, approchee.question, "fr"), confirme_depuis=approchee.id)
    assert st.tableau(7)["questions"] == 1  # la confirmation n'est pas une nouvelle question
    plus_tard = datetime.now(UTC) + timedelta(days=10)
    t = st.tableau(7, maintenant=plus_tard)
    assert (t["questions"], t["questions_periode_precedente"]) == (0, 1)


def test_route_admin(connecter):
    client = TestClient(module_app.app)
    assert client.get("/admin/tableau").status_code == 401
    connecter(client)
    ok = client.get("/admin/tableau?jours=7")
    assert ok.status_code == 200 and ok.json()["jours"] == 7 and ok.headers["cache-control"] == "no-store"
    assert "benchmark" in ok.json()  # dernière exécution du jeu de test (US-28), None s'il n'y en a pas
    assert client.get("/admin/tableau?jours=12").status_code == 422
