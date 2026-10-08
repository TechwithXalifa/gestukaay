import os

# Les tests envoient beaucoup de requêtes depuis la même adresse : limites coupées,
# sauf dans test_securite.py qui les réactive.
os.environ.setdefault("GESTUKAAY_LIMITES", "off")

import pytest
from gestukaay_backend import app as module_app
from gestukaay_backend import comptes
from gestukaay_backend.stockage import Stockage

MOT_DE_PASSE = "mot-de-passe-des-tests"


@pytest.fixture
def base_admin(monkeypatch) -> Stockage:
    """Base neuve avec un compte SAN : le back-office est ouvert (décision 0037)."""
    st = Stockage("")
    st.creer_compte("SAN", comptes.hacher(MOT_DE_PASSE))
    monkeypatch.setattr(module_app, "stockage", st)
    return st


@pytest.fixture
def sans_compte(monkeypatch) -> Stockage:
    """Base neuve sans aucun compte : le back-office n'existe pas."""
    st = Stockage("")
    monkeypatch.setattr(module_app, "stockage", st)
    return st


@pytest.fixture
def connecter(base_admin):
    """connecter(client) ouvre une session SAN sur ce client (cookie gardé par le client)."""
    def _connecter(client, identifiant: str = "SAN", mot_de_passe: str = MOT_DE_PASSE):
        return client.post("/admin/connexion", json={"identifiant": identifiant, "mot_de_passe": mot_de_passe})
    return _connecter
