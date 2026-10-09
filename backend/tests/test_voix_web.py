"""Réponse vocale sur le site (décision 0040) : wolof seulement, note calculée à la demande et gardée en mémoire."""

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend.app import app

client = TestClient(app)
VOIX = {"source": "voix", "audio_retour": True}


@dataclass
class _Note:
    opus: bytes


@pytest.fixture
def voix(monkeypatch):
    """Une voix qui compte ses appels (le faux moteur n'en a pas)."""
    appels = []

    def parler(rep):
        appels.append(rep.reponse.id)
        return _Note(b"OggS-note")

    monkeypatch.setattr(module_app.moteur, "parler", parler)
    module_app._notes.clear()
    return appels


def _poser(question: str, **champs) -> dict:
    r = client.post("/v1/ask", json={"question": question, **champs})
    assert r.status_code == 200
    return r.json()["reponse"]


def test_question_vocale_en_wolof_recoit_une_adresse_audio():
    r = _poser("Ñaata nit ñoo dëkk Tiés ?", **VOIX)
    assert r["langue"] == "wo"
    assert r["audio_url"] == f"/v1/answers/{r['id']}/audio.ogg"
    assert client.get(f"/v1/answers/{r['id']}").json()["reponse"]["audio_url"] == r["audio_url"]  # conservée


def test_question_ecrite_ou_en_francais_sans_voix():
    assert _poser("Ñaata nit ñoo dëkk Tiés ?")["audio_url"] is None  # écrite
    assert _poser("Combien d'habitants à Thiès ?", **VOIX)["audio_url"] is None  # en français : pas de voix fr


def test_la_note_est_dite_une_fois_puis_gardee(voix):
    r = _poser("Ñaata nit ñoo dëkk Tiés ?", **VOIX)
    for _ in range(3):  # durée, lecture, réécoute
        a = client.get(r["audio_url"])
        assert a.status_code == 200
        assert a.headers["content-type"] == "audio/ogg"
        assert a.content == b"OggS-note"
    assert voix == [r["id"]]


def test_pas_de_voix_sans_question_vocale(voix):
    r = _poser("Ñaata nit ñoo dëkk Tiés ?")
    assert client.get(f"/v1/answers/{r['id']}/audio.ogg").status_code == 404
    assert voix == []


def test_voix_indisponible_ou_en_panne_404(monkeypatch):
    module_app._notes.clear()
    r = _poser("Ñaata nit ñoo dëkk Tiés ?", **VOIX)
    assert client.get(r["audio_url"]).status_code == 404  # faux moteur : pas de voix

    def panne(rep):
        raise RuntimeError("service de voix injoignable")

    monkeypatch.setattr(module_app.moteur, "parler", panne)
    assert client.get(r["audio_url"]).status_code == 404


def test_reponse_inconnue_404():
    assert client.get("/v1/answers/inconnue/audio.ogg").status_code == 404
