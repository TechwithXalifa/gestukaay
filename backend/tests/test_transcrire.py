from fastapi.testclient import TestClient
from gestukaay_backend.app import AUDIO_MAX_OCTETS, app
from gestukaay_contracts.models import TranscriptionResponse

client = TestClient(app)


def _envoyer(contenu: bytes, type_mime: str = "audio/webm;codecs=opus", **champs):
    return client.post("/v1/transcrire", files={"fichier": ("q.webm", contenu, type_mime)}, data=champs)


def test_transcription_conforme_au_contrat():
    r = _envoyer(b"\x1a\x45\xdf\xa3audio", langue="auto")
    assert r.status_code == 200
    rep = TranscriptionResponse.model_validate(r.json())
    assert rep.transcription and rep.langue in ("fr", "wo")


def test_ogg_accepte_pour_whatsapp():
    assert _envoyer(b"OggS...", "audio/ogg").status_code == 200


def test_formats_et_tailles_refuses_au_format_problem():
    for r, statut in [
        (_envoyer(b"x", "audio/mpeg"), 415),
        (_envoyer(b""), 422),
        (_envoyer(b"x" * (AUDIO_MAX_OCTETS + 1)), 413),
    ]:
        assert r.status_code == statut
        assert r.headers["content-type"].startswith("application/problem+json")


def test_question_dictee_puis_corrigee():
    r = client.post("/v1/ask", json={
        "question": "Combien d'habitants à Thiès ?",
        "source": "voix",
        "transcription_brute": "Combien d'habitant à Tiès",
    })
    assert r.status_code == 200 and r.json()["reponse"]["issue"] == "exacte"
