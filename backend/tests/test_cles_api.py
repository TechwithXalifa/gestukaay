"""Clés de l'API publique (développeurs) : délivrées et révoquées dans le back-office, limites plus larges."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend import securite

PAUVRETE = "jcvcajc.taux-de-pauvrete"


def test_delivrer_lister_revoquer(connecter, base_admin):
    client = TestClient(module_app.app)
    assert client.get("/admin/cles").status_code == 401  # jamais sans session
    connecter(client)
    r = client.post("/admin/cles", json={"nom": "Le Soleil, rubrique économie"})
    assert r.status_code == 201
    cle = r.json()["cle"]
    assert cle.startswith("gk_") and len(cle) > 30
    [ligne] = client.get("/admin/cles").json()["cles"]
    assert ligne["nom"] == "Le Soleil, rubrique économie" and ligne["creee_par"] == "SAN" and ligne["active"]
    assert cle not in str(ligne) and "empreinte" not in ligne  # la clé n'est montrée qu'une fois

    public = TestClient(module_app.app)
    assert public.get("/v1/indicators", headers={"X-Gestukaay-Cle": cle}).status_code == 200
    assert client.get("/admin/cles").json()["cles"][0]["appels"] == 1

    assert client.post(f"/admin/cles/{ligne['id']}/revoquer").status_code == 204
    r = public.get("/v1/indicators", headers={"X-Gestukaay-Cle": cle})
    assert r.status_code == 401 and r.json()["title"] == "Clé d'API inconnue ou révoquée"
    assert client.post("/admin/cles/inconnue/revoquer").status_code == 404


def test_cle_inconnue_refusee_sans_cle_tout_marche(base_admin):
    public = TestClient(module_app.app)
    assert public.get("/v1/series", params={"indicateur": PAUVRETE}, headers={"X-Gestukaay-Cle": "gk_faux"}).status_code == 401
    assert public.get("/v1/series", params={"indicateur": PAUVRETE}).status_code == 200
    assert public.get("/health", headers={"X-Gestukaay-Cle": "gk_faux"}).status_code == 200  # hors /v1 : ignorée


def test_nom_obligatoire(connecter):
    client = TestClient(module_app.app)
    connecter(client)
    assert client.post("/admin/cles", json={"nom": "x"}).status_code == 422


def test_limites_multipliees_et_comptees_par_cle(monkeypatch):
    monkeypatch.setitem(securite.LIMITES, "explorer", 2)
    lim = securite.Limiteur()
    ip = "41.82.1.1"
    # Avec une clé : 2 x FACTEUR_CLE requêtes, comptées pour la clé, pas pour l'adresse
    passees = [lim.attente(ip, "explorer", 0, cle="c1") == 0 for _ in range(2 * securite.FACTEUR_CLE + 1)]
    assert passees == [True] * (2 * securite.FACTEUR_CLE) + [False]
    assert lim.attente(ip, "explorer", 0) == 0  # la même adresse sans clé garde sa propre limite
    assert lim.attente(ip, "explorer", 0, cle="c2") == 0  # une autre clé non plus


def test_limite_avec_cle_de_bout_en_bout(monkeypatch, connecter):
    monkeypatch.setenv("GESTUKAAY_LIMITES", "on")
    monkeypatch.setitem(securite.LIMITES, "explorer", 1)
    monkeypatch.setattr(module_app, "limiteur", securite.Limiteur())
    client = TestClient(module_app.app)
    connecter(client)
    cle = client.post("/admin/cles", json={"nom": "Essai"}).json()["cle"]
    public = TestClient(module_app.app)
    codes = [public.get("/v1/indicators", headers={"X-Gestukaay-Cle": cle}).status_code
             for _ in range(securite.FACTEUR_CLE + 1)]
    assert codes == [200] * securite.FACTEUR_CLE + [429]
