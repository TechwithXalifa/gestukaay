"""Moteur réel : une fonction pas encore construite répond 503 au format Problem (décision 0019)."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_engine import NonDisponible

client = TestClient(module_app.app)


class _MoteurIncomplet:
    def transcrire(self, *a, **k):
        raise NonDisponible("transcription : pas encore disponible")

    def situer(self, *a, **k):
        raise NonDisponible("« Où je me situe » : pas encore disponible")


def _verifier_503(r):
    assert r.status_code == 503
    assert r.headers["content-type"].startswith("application/problem+json")
    corps = r.json()
    assert corps["status"] == 503 and corps["title"] == "Pas encore disponible"
    assert "#" not in corps["detail"]  # aucun détail interne (numéro de tâche) exposé


def test_situer_non_disponible_rend_503(monkeypatch):
    monkeypatch.setattr(module_app, "moteur", _MoteurIncomplet())
    _verifier_503(client.post("/v1/situate",
                              json={"region": "SN-KD", "taille_menage": 5, "depenses_mensuelles": "100k_200k"}))


def test_transcrire_non_disponible_rend_503(monkeypatch):
    monkeypatch.setattr(module_app, "moteur", _MoteurIncomplet())
    r = client.post("/v1/transcrire", files={"fichier": ("q.webm", b"\x1a\x45\xdf\xa3", "audio/webm")})
    _verifier_503(r)
