from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend import securite

client = TestClient(module_app.app)


def test_limite_de_requetes_429_avec_retry_after(monkeypatch):
    monkeypatch.setenv("GESTUKAAY_LIMITES", "on")
    monkeypatch.setitem(securite.LIMITES, "retour", 3)
    monkeypatch.setattr(module_app, "limiteur", securite.Limiteur())
    corps = {"reponse_id": "inconnue", "type": "vote", "vote": "utile"}
    codes = [client.post("/v1/feedback", json=corps).status_code for _ in range(4)]
    assert codes == [404, 404, 404, 429]
    r = client.post("/v1/feedback", json=corps)
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1
    assert r.headers["content-type"].startswith("application/problem+json")
    assert client.get("/health").status_code == 200  # santé jamais limitée


def test_fenetre_glissante():
    lim = securite.Limiteur()
    assert all(lim.attente("1.2.3.4", "voix", t) == 0 for t in range(10))  # 10 par minute
    assert lim.attente("1.2.3.4", "voix", 30) > 0
    assert lim.attente("5.6.7.8", "voix", 30) == 0  # une autre adresse n'est pas gênée
    assert lim.attente("1.2.3.4", "voix", 61) == 0  # la première requête est sortie de la fenêtre


def test_adresse_derriere_un_proxy(monkeypatch):
    from types import SimpleNamespace

    req = SimpleNamespace(headers={"x-forwarded-for": "41.82.1.1, 10.0.0.2"}, client=SimpleNamespace(host="10.0.0.2"))
    assert securite.adresse(req) == "10.0.0.2"  # sans proxy déclaré, l'en-tête est ignoré
    monkeypatch.setenv("GESTUKAAY_PROXY_DE_CONFIANCE", "1")
    assert securite.adresse(req) == "41.82.1.1"


def test_entetes_de_securite():
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert "content-security-policy" not in client.get("/docs").headers  # Swagger UI garde son CDN


def test_journal_jamais_en_cache(connecter):
    connecte = TestClient(module_app.app)
    connecter(connecte)
    assert connecte.get("/admin/journal").headers["cache-control"] == "no-store"
