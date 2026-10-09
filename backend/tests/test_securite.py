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


def test_une_salle_derriere_la_meme_adresse(monkeypatch):
    """Audit du 09/10 : 30 onglets sur le même Wi-Fi posent chacun leurs questions ; un robot qui change
    d'identifiant à chaque requête reste borné par le plafond de l'adresse."""
    monkeypatch.setitem(securite.LIMITES, "question", 2)
    monkeypatch.setenv("GESTUKAAY_PLAFOND_IP", "3")
    ip = "41.82.1.1"
    lim = securite.Limiteur()
    # plafond de l'adresse : 2 x 3 = 6 requêtes ; 6 onglets passent, le 7e est bloqué
    assert [lim.attente(ip, "question", 0, client=f"onglet-{n:04d}") == 0 for n in range(7)] == [True] * 6 + [False]
    lim2 = securite.Limiteur()
    # un même onglet a sa propre limite (2), sans gêner les autres
    assert [lim2.attente(ip, "question", t, client="onglet-aaaa") == 0 for t in range(3)] == [True, True, False]
    assert lim2.attente(ip, "question", 3, client="onglet-bbbb") == 0
    assert lim2.attente("5.6.7.8", "question", 3) == 0  # sans en-tête : par adresse, comme avant


def test_identifiant_d_onglet_mal_forme_ignore():
    from types import SimpleNamespace

    assert securite.client(SimpleNamespace(headers={"x-gestukaay-client": "court"})) is None
    assert securite.client(SimpleNamespace(headers={"x-gestukaay-client": "a" * 65})) is None
    assert securite.client(SimpleNamespace(headers={"x-gestukaay-client": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"}))


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



def test_jeton_de_verification_masque_dans_le_journal():
    """09/10 : le journal d'accès d'uvicorn écrivait hub.verify_token en clair."""
    import logging

    r = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d', (
        "1.2.3.4:0", "GET", "/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=secret123&hub_verify_token=secret123",
        "1.1", 200), None)
    module_app.MasquerJetons().filter(r)
    assert "secret123" not in r.getMessage() and "verify_token=***" in r.getMessage()
