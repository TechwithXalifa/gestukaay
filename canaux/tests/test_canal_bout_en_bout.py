"""Bout en bout : un message WhatsApp signé arrive sur le webhook du backend (#119), notre canal le
traite avec le faux moteur et répond à Meta (simulé). Ni réseau, ni socle."""

import hashlib
import hmac
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_canaux.textes import texte
from gestukaay_canaux.whatsapp import CanalWhatsApp, ClientGraph

EXEMPLES = Path(__file__).parents[2] / "contracts" / "examples"
SECRET = "secret-meta-test"


@pytest.fixture
def meta(monkeypatch):
    envois = []

    def gerer(r: httpx.Request):
        envois.append(json.loads(r.content))
        return httpx.Response(200, json={"messages": [{"id": "wamid.REPONSE"}]})
    monkeypatch.setitem(module_app.canaux, "whatsapp", CanalWhatsApp(ClientGraph(httpx.MockTransport(gerer))))
    for k, v in {"WHATSAPP_APP_SECRET": SECRET, "WHATSAPP_TOKEN": "jeton-meta",
                 "WHATSAPP_PHONE_NUMBER_ID": "1331556276698765"}.items():
        monkeypatch.setenv(k, v)
    return envois


def poster(corps: bytes):
    signature = "sha256=" + hmac.new(SECRET.encode(), corps, hashlib.sha256).hexdigest()
    return TestClient(module_app.app).post("/webhooks/whatsapp", content=corps, headers={
        "X-Hub-Signature-256": signature, "Content-Type": "application/json"})


def test_question_ecrite_de_bout_en_bout(meta):
    # numéro propre à ce test : la base en mémoire est partagée avec les tests du backend
    corps = (EXEMPLES / "whatsapp" / "texte.json").read_bytes().replace(b"wamid.TEXTE0001", b"wamid.BOUT0001")
    corps = corps.replace(b"221700000001", b"221700009999")
    assert poster(corps).status_code == 200
    lu, *textes = meta
    assert lu["status"] == "read" and lu["typing_indicator"] == {"type": "text"}
    corps_envoyes = [t["text"]["body"] for t in textes]
    assert texte("accueil") in corps_envoyes  # premier message de cette conversation
    reponse = corps_envoyes[-1]
    # adresse publique par défaut (http://localhost:3000) : pas de lien, il n'ouvrirait rien sur un téléphone (#228)
    assert "Thiès" in reponse and "localhost" not in reponse and reponse.endswith("— gestukaay")
    assert all(t["to"] == "221700009999" for t in textes)


def test_meme_message_renvoye_par_meta_traite_une_fois(meta):
    corps = (EXEMPLES / "whatsapp" / "texte.json").read_bytes().replace(b"wamid.TEXTE0001", b"wamid.BOUT0002")
    poster(corps)
    n = len(meta)
    poster(corps)
    assert len(meta) == n
