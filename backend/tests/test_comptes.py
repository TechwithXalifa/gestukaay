"""Connexion au back-office par identifiant et mot de passe (décision 0037)."""

from datetime import UTC, datetime, timedelta

import pytest
from conftest import MOT_DE_PASSE
from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend import comptes
from gestukaay_backend.stockage import Stockage


@pytest.fixture
def client():
    return TestClient(module_app.app)


def test_hachage_sale_et_verifie():
    h = comptes.hacher(MOT_DE_PASSE)
    assert h.startswith("scrypt$") and MOT_DE_PASSE not in h
    assert h != comptes.hacher(MOT_DE_PASSE)  # sel propre à chaque hachage
    assert comptes.verifier(MOT_DE_PASSE, h) and not comptes.verifier("autre-mot-de-passe", h)


def test_ferme_sans_compte(sans_compte, client):
    assert client.post("/admin/connexion", json={"identifiant": "SAN", "mot_de_passe": "x"}).status_code == 404
    assert client.get("/admin/moi").status_code == 404


def test_connexion_cookie_et_deconnexion(connecter, client):
    assert client.get("/admin/moi").status_code == 401
    r = connecter(client, "san")  # l'identifiant est comparé sans la casse
    assert r.status_code == 200 and r.json() == {"identifiant": "SAN"}
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/admin" in cookie
    assert client.get("/admin/moi").json() == {"identifiant": "SAN"}
    assert client.post("/admin/deconnexion").status_code == 204
    assert client.get("/admin/moi").status_code == 401


def test_meme_refus_quel_que_soit_le_motif(connecter, base_admin, client):
    faux = connecter(client, "SAN", "mauvais-mot-de-passe")
    inconnu = connecter(client, "PERSONNE", MOT_DE_PASSE)
    assert faux.status_code == inconnu.status_code == 401 and faux.json() == inconnu.json()
    assert "set-cookie" not in faux.headers
    base_admin.desactiver_compte("SAN")
    base_admin.creer_compte("KBD", comptes.hacher(MOT_DE_PASSE))  # le back-office reste ouvert
    assert connecter(client, "SAN").json() == faux.json()


def test_blocage_apres_cinq_essais(connecter, client):
    for _ in range(comptes.ESSAIS_MAX):
        assert connecter(client, "SAN", "mauvais-mot-de-passe").status_code == 401
    assert connecter(client).status_code == 401  # bon mot de passe, mais compte bloqué
    st: Stockage = module_app.stockage
    plus_tard = datetime.now(UTC) + comptes.BLOCAGE + timedelta(seconds=1)
    assert comptes.connecter(st, "SAN", MOT_DE_PASSE, plus_tard)


def test_expiration_de_la_session(base_admin):
    debut = datetime.now(UTC)
    jeton = comptes.connecter(base_admin, "SAN", MOT_DE_PASSE, debut)
    assert comptes.identifier(base_admin, jeton, debut + timedelta(hours=7)) == "SAN"  # prolongée
    assert comptes.identifier(base_admin, jeton, debut + timedelta(hours=11)) == "SAN"
    assert comptes.identifier(base_admin, jeton, debut + comptes.DUREE_MAX + timedelta(seconds=1)) is None
    jeton = comptes.connecter(base_admin, "SAN", MOT_DE_PASSE, debut)
    assert comptes.identifier(base_admin, jeton, debut + comptes.INACTIVITE + timedelta(seconds=1)) is None


def test_la_base_ne_garde_pas_le_jeton(base_admin):
    jeton = comptes.connecter(base_admin, "SAN", MOT_DE_PASSE)
    assert jeton and not base_admin._executer("SELECT 1 FROM sessions_admin WHERE jeton = ?", (jeton,))


def test_nouveau_mot_de_passe_ferme_les_sessions(connecter, base_admin, client):
    connecter(client)
    base_admin.changer_mot_de_passe("SAN", comptes.hacher("un-tout-nouveau-mot"))
    assert client.get("/admin/moi").status_code == 401


def test_post_d_un_autre_site_refuse(connecter, client):
    autre = {"Origin": "https://site-malveillant.example"}
    assert client.post("/admin/connexion", json={"identifiant": "SAN", "mot_de_passe": MOT_DE_PASSE},
                       headers=autre).status_code == 403
    connecter(client)
    assert client.post("/admin/jeu-de-test/executions", json={"mode": "regles"}, headers=autre).status_code == 403
    site = {"Origin": module_app.ORIGINES[0]}
    assert client.post("/admin/deconnexion", headers=site).status_code == 204


def test_ligne_de_commande(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GESTUKAAY_BASE", f"sqlite:///{tmp_path / 'g.db'}")
    monkeypatch.setattr(comptes, "_lire_mot_de_passe", lambda: MOT_DE_PASSE)
    comptes.main(["creer", "KBD"])
    with pytest.raises(SystemExit, match="existe déjà"):
        comptes.main(["creer", "kbd"])
    comptes.main(["desactiver", "KBD"])
    comptes.main(["lister"])
    assert "KBD\tdésactivé" in capsys.readouterr().out
    comptes.main(["changer", "KBD"])  # réactive
    assert comptes.connecter(Stockage(), "KBD", MOT_DE_PASSE)
    monkeypatch.setattr(comptes, "_lire_mot_de_passe", lambda: "court")
    with pytest.raises(SystemExit, match="trop court"):
        comptes.main(["creer", "SAN"])
    with pytest.raises(SystemExit, match="Identifiant"):
        comptes.main(["creer", "S A N"])


def test_mot_de_passe_sans_terminal(monkeypatch):  # e2e : variable d'environnement, sinon une ligne par tube
    import io
    monkeypatch.setenv("GESTUKAAY_MOT_DE_PASSE", "un mot de passe long")
    assert comptes._lire_mot_de_passe() == "un mot de passe long"
    monkeypatch.delenv("GESTUKAAY_MOT_DE_PASSE")
    monkeypatch.setattr("sys.stdin", io.StringIO("avec espace final \r\n"))
    assert comptes._lire_mot_de_passe() == "avec espace final "  # le \r\n part, l'espace reste
