"""Lexique grand public et wolof (back-office, #23) : seules les entrées validées réécrivent la question."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend.lexique import Entree, appliquer, motif


def test_mots_entiers_sans_casse_ni_accents():
    e = [Entree("1", "les mamans", "les femmes"), Entree("2", "menages", "ménages")]
    assert appliquer("Combien de Mamans à Kolda ?", e) == ("Combien de Mamans à Kolda ?", [])  # « de Mamans » ≠ « les mamans »
    texte, appliquees = appliquer("Et pour les MAMANS ?", e)
    assert texte == "Et pour les femmes ?" and [a.id for a in appliquees] == ["1"]
    assert appliquer("Argent des ménages", [Entree("3", "argent des menages", "consommation des ménages")])[0] == \
        "consommation des ménages"
    assert not motif("riz").search("Prix du rizière")  # mot entier seulement
    assert motif("aujourd'hui").search("aujourd’hui")  # apostrophe courbe ou droite


def test_la_plus_longue_d_abord_et_remplacement_tel_quel():
    e = [Entree("1", "chômage", "taux de chômage"), Entree("2", "chômage des jeunes", "taux de chômage des 15-24 ans")]
    assert appliquer("chômage des jeunes à Dakar", e)[0] == "taux de chômage des 15-24 ans à Dakar"
    assert appliquer("prix", [Entree("3", "prix", r"\1 coût")])[0] == r"\1 coût"  # jamais une référence de groupe
    long = [Entree("4", "a", "x" * 400)]
    assert appliquer("a b", long) == ("a b", [])  # trop long pour le moteur : la question part telle quelle


def test_proposer_valider_essayer_exporter_et_appliquer(connecter, base_admin, monkeypatch):
    client = TestClient(module_app.app)
    assert client.get("/admin/lexique").status_code == 401
    connecter(client)
    r = client.post("/admin/lexique", json={"expression": "les mamans", "remplacement": "les femmes", "langue": "fr",
                                             "note": "test grand public (#280)"})
    assert r.status_code == 201
    eid = r.json()["id"]
    assert client.post("/admin/lexique", json={"expression": "Les  MAMANS", "remplacement": "x", "langue": "fr"}).status_code == 409

    vues: list[str] = []
    repondre = module_app.moteur.repondre
    monkeypatch.setattr(module_app.moteur, "repondre", lambda req, ctx=None: vues.append(req.question) or repondre(req, ctx))

    # Proposée : rien ne change
    assert client.post("/admin/lexique/essai", json={"question": "Et pour les mamans ?"}).json()["appliquees"] == []
    client.post("/v1/ask", json={"question": "Combien d'habitants à Thiès pour les mamans ?"})
    assert vues[-1] == "Combien d'habitants à Thiès pour les mamans ?"

    # Validée : le moteur reçoit la question réécrite, l'usager et le journal gardent la sienne
    assert client.post(f"/admin/lexique/{eid}/statut", json={"statut": "valide"}).status_code == 204
    essai = client.post("/admin/lexique/essai", json={"question": "Et pour les mamans ?"}).json()
    assert essai["transformee"] == "Et pour les femmes ?"
    rep = client.post("/v1/ask", json={"question": "Combien d'habitants à Thiès pour les mamans ?"}).json()["reponse"]
    assert vues[-1] == "Combien d'habitants à Thiès pour les femmes ?"
    assert rep["question"] == "Combien d'habitants à Thiès pour les mamans ?"
    assert client.get("/admin/journal").json()["lignes"][0]["question"] == "Combien d'habitants à Thiès pour les mamans ?"
    [entree] = client.get("/admin/lexique", params={"statut": "valide"}).json()["entrees"]
    assert entree["utilisations"] == 1 and entree["decide_par"] == "SAN"

    csv = client.get("/admin/lexique.csv")
    assert csv.status_code == 200 and "les mamans" in csv.content.decode("utf-16")

    # Rejetée : plus rien
    client.post(f"/admin/lexique/{eid}/statut", json={"statut": "rejete"})
    client.post("/v1/ask", json={"question": "Combien d'habitants à Thiès pour les mamans ?"})
    assert vues[-1].endswith("les mamans ?")
    assert client.post("/admin/lexique/inconnu/statut", json={"statut": "valide"}).status_code == 404
