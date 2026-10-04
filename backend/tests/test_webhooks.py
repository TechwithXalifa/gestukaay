"""Webhooks WhatsApp et Telegram (EF-19, EF-24, 10.7) : la partie transport du backend.

Le module de canal de KBD n'existe pas encore : un faux canal lit les payloads d'exemple
(contracts/examples/whatsapp, telegram) et appelle les services comme le fera le vrai.
"""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend.canaux import Entrant, Services
from gestukaay_backend.stockage import FiltreJournal

client = TestClient(module_app.app)
EXEMPLES = Path(__file__).parents[2] / "contracts" / "examples"
SECRET, JETON, TG = "secret-meta", "jeton-verification", "secret-telegram"
NUMERO = "221700000001"


def exemple(nom: str) -> bytes:
    return (EXEMPLES / nom).read_bytes()


def signer(corps: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), corps, hashlib.sha256).hexdigest()


class FauxWhatsApp:
    """Ce que fera le module de KBD, réduit au strict nécessaire pour tester le transport."""

    nom = "whatsapp"

    def __init__(self):
        self.traites: list[tuple[Entrant, object]] = []

    def lire(self, payload: dict) -> list[Entrant]:
        out = []
        for entree in payload["entry"]:
            for changement in entree["changes"]:
                for m in changement["value"].get("messages", []):
                    out.append(Entrant(m["id"], m["from"], m))
        return out

    def traiter(self, entrant: Entrant, services: Services) -> None:
        m = entrant.contenu
        if m["type"] == "text":
            rep = services.demander(m["text"]["body"])
        elif m["type"] == "interactive":
            precedente = services.derniere()
            rep = services.confirmer(precedente.reponse.id, m["interactive"]["list_reply"]["id"].removeprefix("choix-"))
        else:
            rep = None
        self.traites.append((entrant, rep))


class FauxTelegram:
    nom = "telegram"

    def __init__(self):
        self.traites: list[Entrant] = []

    def lire(self, payload: dict) -> list[Entrant]:
        return [Entrant(str(payload["update_id"]), str(payload["message"]["chat"]["id"]), payload["message"])]

    def traiter(self, entrant: Entrant, services: Services) -> None:
        if "text" in entrant.contenu:
            services.demander(entrant.contenu["text"])
        self.traites.append(entrant)


@pytest.fixture
def wa(monkeypatch):
    canal = FauxWhatsApp()
    monkeypatch.setitem(module_app.canaux, "whatsapp", canal)
    monkeypatch.setenv("WHATSAPP_APP_SECRET", SECRET)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", JETON)
    return canal


def poster(corps: bytes, signature: str | None = None):
    return client.post("/webhooks/whatsapp", content=corps,
                       headers={"X-Hub-Signature-256": signature or signer(corps), "Content-Type": "application/json"})


def test_ferme_sans_module_ou_sans_secret(monkeypatch):
    monkeypatch.delitem(module_app.canaux, "whatsapp", raising=False)
    monkeypatch.setenv("WHATSAPP_APP_SECRET", SECRET)
    assert poster(exemple("whatsapp/texte.json")).status_code == 404
    monkeypatch.setitem(module_app.canaux, "whatsapp", FauxWhatsApp())
    monkeypatch.delenv("WHATSAPP_APP_SECRET")
    assert poster(exemple("whatsapp/texte.json")).status_code == 404


def test_verification_de_l_abonnement(wa):
    ok = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": JETON,
                                                  "hub.challenge": "1158201444"})
    assert ok.status_code == 200 and ok.text == "1158201444"
    faux = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "faux",
                                                    "hub.challenge": "1"})
    assert faux.status_code == 403


def test_signature_obligatoire(wa):
    corps = exemple("whatsapp/texte.json")
    assert poster(corps, signature="sha256=" + "0" * 64).status_code == 403
    assert poster(corps, signature=signer(corps, "autre-secret")).status_code == 403
    assert client.post("/webhooks/whatsapp", content=corps).status_code == 403  # sans en-tête
    assert wa.traites == []


def test_question_traitee_en_tache_de_fond_et_numero_jamais_garde(wa):
    r = poster(exemple("whatsapp/texte.json"))
    assert r.status_code == 200 and r.json() == {"statut": "recu", "messages": 1}
    _, rep = wa.traites[-1]
    assert rep.reponse.issue == "exacte"
    ligne = next(lg for lg in module_app.stockage.journal(FiltreJournal(canal="whatsapp"))[1]
                 if lg["reponse_id"] == rep.reponse.id)
    assert ligne["canal"] == "whatsapp" and ligne["conversation"]
    assert NUMERO not in json.dumps(ligne)  # haché, jamais en clair


def test_un_message_n_est_traite_qu_une_fois(wa):
    corps = exemple("whatsapp/texte.json").replace(b"wamid.TEXTE0001", b"wamid.DOUBLON01")
    assert poster(corps).json()["messages"] == 1
    assert poster(corps).json()["messages"] == 0  # Meta renvoie le même message : ignoré
    assert sum(1 for e, _ in wa.traites if e.message_id == "wamid.DOUBLON01") == 1


def test_un_statut_ne_declenche_rien(wa):
    r = poster(exemple("whatsapp/statut.json"))
    assert r.status_code == 200 and r.json()["messages"] == 0 and wa.traites == []


def test_choix_numerote_apres_une_reponse_approchee(wa):
    question = exemple("whatsapp/texte.json").replace(b"wamid.TEXTE0001", b"wamid.APPROCH01").replace(
        "Combien d'habitants à Thiès ?".encode(), "Population de la ville de Thiès en 2023".encode())
    poster(question)
    assert wa.traites[-1][1].reponse.issue == "approchee"
    poster(exemple("whatsapp/reponse_choix.json"))
    _, confirmee = wa.traites[-1]
    assert confirmee.reponse.issue == "exacte"  # services.derniere() a retrouvé l'approchée de la conversation


def test_une_erreur_du_canal_ne_remonte_pas_a_meta(wa, monkeypatch, caplog):
    def echec(entrant, services):
        raise RuntimeError("Graph API indisponible")

    monkeypatch.setattr(wa, "traiter", echec)
    corps = exemple("whatsapp/texte.json").replace(b"wamid.TEXTE0001", b"wamid.ERREUR01")
    with caplog.at_level(logging.ERROR, logger="gestukaay.webhooks"):
        assert poster(corps).status_code == 200
    assert "wamid.ERREUR01" in caplog.text and NUMERO not in caplog.text


def test_payload_illisible_journalise_sans_erreur(wa):
    corps = b'{"object": "autre"}'
    r = poster(corps)
    assert r.status_code == 200 and r.json() == {"statut": "ignore"}


def test_unicite_purgee_apres_48_heures():
    st = module_app.stockage
    assert st.premier_passage("whatsapp", "wamid.PURGE01")
    assert not st.premier_passage("whatsapp", "wamid.PURGE01")
    plus_tard = datetime.now(UTC) + timedelta(hours=49)
    assert st.premier_passage("whatsapp", "wamid.PURGE01", maintenant=plus_tard)


def test_telegram(monkeypatch):
    canal = FauxTelegram()
    monkeypatch.setitem(module_app.canaux, "telegram", canal)
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", TG)
    corps = exemple("telegram/texte.json")
    assert client.post("/webhooks/telegram", content=corps,
                       headers={"X-Telegram-Bot-Api-Secret-Token": "faux"}).status_code == 403
    r = client.post("/webhooks/telegram", content=corps, headers={"X-Telegram-Bot-Api-Secret-Token": TG})
    assert r.status_code == 200 and r.json()["messages"] == 1 and canal.traites[-1].message_id == "500000001"
    r = client.post("/webhooks/telegram", content=corps, headers={"X-Telegram-Bot-Api-Secret-Token": TG})
    assert r.json()["messages"] == 0
