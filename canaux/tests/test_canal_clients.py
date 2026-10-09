"""Lecture des payloads réels (exemples d'Aziz) et appels à Meta / Telegram, simulés (httpx.MockTransport)."""

import json
import traceback
from pathlib import Path

import httpx
import pytest
from gestukaay_canaux import media, telegram, whatsapp
from gestukaay_canaux.conversation import Contenu
from gestukaay_contracts.models import AskResponse

EXEMPLES = Path(__file__).parents[2] / "contracts" / "examples"
JETON_TG = "123456:SECRET-DU-BOT"


def payload(nom: str) -> dict:
    return json.loads((EXEMPLES / nom).read_text(encoding="utf-8"))


def test_lire_whatsapp():
    [t] = whatsapp.lire(payload("whatsapp/texte.json"))
    assert (t.message_id, t.expediteur, t.contenu.type, t.contenu.texte) == \
        ("wamid.TEXTE0001", "221700000001", "texte", "Combien d'habitants à Thiès ?")
    [a] = whatsapp.lire(payload("whatsapp/audio.json"))
    assert (a.contenu.type, a.contenu.media) == ("audio", "300000000000001")
    [c] = whatsapp.lire(payload("whatsapp/reponse_choix.json"))
    assert (c.contenu.type, c.contenu.choix_id) == ("choix", "1")
    assert whatsapp.lire(payload("whatsapp/statut.json")) == []


def test_lire_telegram():
    [t] = telegram.lire(payload("telegram/texte.json"))
    assert (t.message_id, t.expediteur, t.contenu.type) == ("500000001", "600000001", "texte")
    [v] = telegram.lire(payload("telegram/voix.json"))
    assert (v.contenu.type, v.contenu.media) == ("audio", "AwACAgQAAxkBAAExemple")
    rappel = {"update_id": 9, "callback_query": {"id": "cb1", "data": "choix-2",
                                                 "message": {"chat": {"id": 600000001}}}}
    [c] = telegram.lire(rappel)
    assert (c.contenu.type, c.contenu.choix_id, c.contenu.accuse) == ("choix", "2", "cb1")


@pytest.fixture
def graph(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "jeton-meta")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1331556276698765")
    requetes = []

    def gerer(r: httpx.Request):
        requetes.append(r)
        if r.method == "GET" and r.url.path.endswith("/300000000000001"):
            return httpx.Response(200, json={"url": "https://lookaside.fbsbx.com/media/abc"})
        if r.method == "GET":
            return httpx.Response(200, content=b"OggS-audio")
        return httpx.Response(200, json={"messages": [{"id": "wamid.REPONSE"}]})
    return whatsapp.ClientGraph(httpx.MockTransport(gerer)), requetes


def test_graph_lu_et_en_train_d_ecrire_puis_texte(graph):
    client, requetes = graph
    client.accuser("221700000001", Contenu("texte", accuse="wamid.TEXTE0001"))
    client.texte("221700000001", "Bonjour")
    lu, envoi = (json.loads(r.content) for r in requetes)
    assert requetes[0].url == "https://graph.facebook.com/v25.0/1331556276698765/messages"
    assert requetes[0].headers["Authorization"] == "Bearer jeton-meta"
    assert lu == {"messaging_product": "whatsapp", "status": "read", "message_id": "wamid.TEXTE0001",
                  "typing_indicator": {"type": "text"}}
    assert envoi["to"] == "221700000001" and envoi["text"] == {"preview_url": False, "body": "Bonjour"}


def test_graph_liste_de_choix_dans_les_limites_de_meta(graph):
    client, requetes = graph
    r = AskResponse.model_validate_json((EXEMPLES / "approchee.json").read_text(encoding="utf-8"))
    client.choix("221700000001", r.reponse.choix)
    i = json.loads(requetes[0].content)["interactive"]
    assert len(i["action"]["button"]) <= 20 and len(i["body"]["text"]) <= 1024
    for ligne, c in zip(i["action"]["sections"][0]["rows"], r.reponse.choix, strict=True):
        assert ligne["id"] == f"choix-{c.id}" and len(ligne["title"]) <= 24 and len(ligne["description"]) <= 72


def test_graph_telecharge_la_note_vocale_en_deux_temps(graph):
    client, requetes = graph
    assert client.media(Contenu("audio", media="300000000000001")) == b"OggS-audio"
    assert [str(r.url) for r in requetes] == ["https://graph.facebook.com/v25.0/300000000000001",
                                               "https://lookaside.fbsbx.com/media/abc"]
    assert all(r.headers["Authorization"] == "Bearer jeton-meta" for r in requetes)


@pytest.mark.parametrize("annoncee", [True, False])  # taille annoncée, ou cachée (lecture par morceaux)
def test_graph_note_de_plus_de_2_mo_refusee(monkeypatch, annoncee):
    monkeypatch.setenv("WHATSAPP_TOKEN", "jeton-meta")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1331556276698765")
    gros = b"x" * (media.OCTETS_MAX + 1)

    def gerer(r: httpx.Request):
        if r.url.path.endswith("/300000000000001"):
            return httpx.Response(200, json={"url": "https://lookaside.fbsbx.com/media/abc"})
        if annoncee:
            return httpx.Response(200, content=gros)
        return httpx.Response(200, content=iter([gros[:1024 * 1024]] * 3))  # sans content-length
    with pytest.raises(media.NoteTropGrosse):
        whatsapp.ClientGraph(httpx.MockTransport(gerer)).media(Contenu("audio", media="300000000000001"))


def test_telegram_erreur_sans_le_jeton_du_bot(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", JETON_TG)

    def panne(r: httpx.Request):
        raise httpx.ConnectError("échec", request=r)
    client = telegram.ClientTelegram(httpx.MockTransport(panne))
    with pytest.raises(telegram.ErreurTelegram) as e:
        client.texte("600000001", "Bonjour")
    trace = "".join(traceback.format_exception(e.value))  # ce que le backend journaliserait
    assert JETON_TG not in trace and "sendMessage" in trace


def test_graph_note_vocale_deposee_puis_envoyee(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "jeton-meta")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1331556276698765")
    requetes = []

    def gerer(r: httpx.Request):
        requetes.append(r)
        if r.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "media-123"})
        return httpx.Response(200, json={"messages": [{"id": "wamid.VOIX"}]})
    whatsapp.ClientGraph(httpx.MockTransport(gerer)).vocal("221700000001", b"OggS-note")
    depot, envoi = requetes
    assert depot.url.path == "/v25.0/1331556276698765/media" and b"OggS-note" in depot.content
    assert b"audio/ogg" in depot.content and depot.headers["Authorization"] == "Bearer jeton-meta"
    assert json.loads(envoi.content) == {"messaging_product": "whatsapp", "recipient_type": "individual",
                                         "to": "221700000001", "type": "audio",
                                         "audio": {"id": "media-123", "voice": True}}


def test_telegram_note_vocale_sans_le_jeton_dans_l_erreur(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", JETON_TG)
    requetes = []

    def gerer(r: httpx.Request):
        requetes.append(r)
        return httpx.Response(200, json={"ok": True, "result": {}})
    client = telegram.ClientTelegram(httpx.MockTransport(gerer))
    client.preparer_vocal("600000001")
    client.vocal("600000001", b"OggS-note")
    assert json.loads(requetes[0].content) == {"chat_id": "600000001", "action": "record_voice"}
    assert requetes[1].url.path.endswith("/sendVoice") and b"OggS-note" in requetes[1].content

    def panne(r: httpx.Request):
        raise httpx.ConnectError("échec", request=r)
    with pytest.raises(telegram.ErreurTelegram) as e:
        telegram.ClientTelegram(httpx.MockTransport(panne)).vocal("600000001", b"OggS")
    assert JETON_TG not in "".join(traceback.format_exception(e.value))


def test_whatsapp_refus_de_meta_journalise_sans_numero(caplog, monkeypatch):
    # essai réel du 07/10 : le 400 de Meta (131030, destinataire hors liste de test) n'était pas lisible.
    # Revue de SAN : par le vrai envoi ; l'erreur part toujours, le journal n'a ni le numéro ni le texte.
    import logging

    import httpx
    import pytest
    from gestukaay_canaux.whatsapp import ClientGraph

    refus = {"error": {"code": 131030, "message": "(#131030) Recipient phone number not in allowed list",
                       "error_data": {"details": "Ajoutez le numéro"}}}
    monkeypatch.setenv("WHATSAPP_TOKEN", "jeton-de-test")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1000")
    client = ClientGraph(transport=httpx.MockTransport(lambda r: httpx.Response(400, json=refus)))
    with caplog.at_level(logging.WARNING), pytest.raises(httpx.HTTPStatusError):
        client.texte("221770000000", "Combien d'habitants à Thiès ?")
    assert "131030" in caplog.text and "allowed list" in caplog.text
    assert "221770000000" not in caplog.text and "habitants" not in caplog.text


@pytest.mark.parametrize("corps", [["inattendu"], "texte", {"error": "proxy"}, {"error": {"code": 1, "error_data": "x"}}])
def test_raison_meta_corps_inattendu(corps):  # revue de SAN : jamais d'AttributeError qui cache le 400
    import httpx
    from gestukaay_canaux.whatsapp import _raison_meta
    assert _raison_meta(httpx.Response(400, json=corps)).startswith("HTTP 400")


def test_statut_non_remis_journalise_sans_numero(caplog):
    # essai réel du 07/10 : envois acceptés mais jamais remis (131031, compte verrouillé)
    import logging

    from gestukaay_canaux.whatsapp import lire
    statut = {"entry": [{"changes": [{"value": {"statuses": [{
        "id": "wamid.X", "status": "failed", "recipient_id": "221770000000",
        "errors": [{"code": 131031, "title": "Business Account locked"}]}]}}]}]}
    with caplog.at_level(logging.WARNING):
        assert lire(statut) == []
    assert "131031" in caplog.text and "221770000000" not in caplog.text


@pytest.fixture
def transport_retente(monkeypatch):
    """Remplace le transport réel de `media.relance` : on voit comment il est créé et lequel sert."""
    for nom in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy", "NO_PROXY",
                "no_proxy"):
        monkeypatch.delenv(nom, raising=False)
    crees, requetes = [], []

    class Retente(httpx.MockTransport):
        def __init__(self, **kw):
            crees.append(kw)
            super().__init__(lambda r: requetes.append((kw.get("proxy"), r.url.host))
                             or httpx.Response(200, json={"ok": True, "result": {}}))
    monkeypatch.setattr(httpx, "HTTPTransport", Retente)
    return crees, requetes


def test_connexion_retentee_hors_tests_telegram_et_meta(monkeypatch, transport_retente):
    # essais du 09/10 : api.telegram.org injoignable par moments (ConnectTimeout), réponse jamais partie
    crees, requetes = transport_retente
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", JETON_TG)
    monkeypatch.setenv("WHATSAPP_TOKEN", "jeton-meta")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1331556276698765")
    telegram.ClientTelegram().texte("600000001", "Bonjour")
    whatsapp.ClientGraph().texte("221700000001", "Bonjour")
    assert crees == [{"retries": media.RELANCES}] * 2 and media.RELANCES >= 1
    assert requetes == [(None, "api.telegram.org"), (None, "graph.facebook.com")]


def test_relance_garde_le_proxy_de_l_environnement(monkeypatch, transport_retente):
    # un `transport` explicite couperait HTTPS_PROXY : le proxy de l'environnement reste prioritaire (sans relance, #244)
    _, requetes = transport_retente
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")  # port fermé : la connexion au proxy échoue
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", JETON_TG)
    with pytest.raises(telegram.ErreurTelegram):
        telegram.ClientTelegram().texte("600000001", "Bonjour")
    assert requetes == []  # passé par le proxy, pas par le transport direct
