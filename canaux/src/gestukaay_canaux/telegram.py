"""Bot Telegram de secours (EF-24, #36) : même conversation que WhatsApp (décision 0025).

Configuration (`.env`, jamais dans Git) : TELEGRAM_BOT_TOKEN. Le jeton du bot fait partie de l'adresse
de l'API Telegram : une erreur réseau est donc relancée SANS son adresse, pour qu'il n'arrive jamais
dans les journaux du backend.
"""

from __future__ import annotations

import os

import httpx
from gestukaay_backend.canaux import Entrant, Services
from gestukaay_contracts.models import Choix

from .conversation import Contenu, traiter
from .media import relance, telecharger
from .textes import texte

DELAI_S = 10


def lire(update: dict) -> list[Entrant]:
    ident = str(update.get("update_id", ""))
    if q := update.get("callback_query"):  # toucher sur un bouton de choix
        chat = str((q.get("message") or {}).get("chat", {}).get("id", ""))
        data = q.get("data", "")
        if not chat or not data.startswith("choix-"):
            return []
        return [Entrant(ident, chat, Contenu("choix", choix_id=data.removeprefix("choix-"), accuse=q["id"]))]
    m = update.get("message")
    if not m:
        return []
    chat = str(m.get("chat", {}).get("id", ""))
    if "text" in m:
        return [Entrant(ident, chat, Contenu("texte", texte=m["text"]))]
    if "voice" in m or "audio" in m:
        return [Entrant(ident, chat, Contenu("audio", media=(m.get("voice") or m.get("audio"))["file_id"]))]
    return [Entrant(ident, chat, Contenu("autre"))]


class ErreurTelegram(RuntimeError):
    """Échec d'un appel à l'API Telegram, sans l'adresse (qui contient le jeton du bot)."""


class ClientTelegram:
    gras = False  # texte brut : pas de mise en forme à échapper

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def _jeton(self) -> str:
        jeton = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not jeton:
            raise ErreurTelegram("TELEGRAM_BOT_TOKEN absent de l'environnement")
        return jeton

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=DELAI_S, transport=self._transport, mounts=relance(self._transport))

    def _appel(self, methode: str, corps: dict) -> dict:
        try:
            with self._client() as h:
                r = h.post(f"https://api.telegram.org/bot{self._jeton()}/{methode}", json=corps)
                r.raise_for_status()
                return r.json().get("result") or {}
        except httpx.HTTPError as e:
            raise ErreurTelegram(f"Telegram {methode} : {type(e).__name__}") from None

    def accuser(self, destinataire: str, contenu: Contenu) -> None:
        if contenu.accuse:  # toucher sur un bouton : Telegram attend une réponse au rappel
            self._appel("answerCallbackQuery", {"callback_query_id": contenu.accuse})
        self._appel("sendChatAction", {"chat_id": destinataire, "action": "typing"})

    def texte(self, destinataire: str, message: str) -> None:
        self._appel("sendMessage", {"chat_id": destinataire, "text": message[:4096],
                                    "link_preview_options": {"is_disabled": True}})

    def choix(self, destinataire: str, choix: list[Choix]) -> None:
        boutons = [[{"text": f"{c.id}. {c.libelle}"[:60], "callback_data": f"choix-{c.id}"}] for c in choix]
        self._appel("sendMessage", {"chat_id": destinataire, "text": texte("choisir"),
                                    "reply_markup": {"inline_keyboard": boutons}})

    def preparer_vocal(self, destinataire: str) -> None:
        self._appel("sendChatAction", {"chat_id": destinataire, "action": "record_voice"})

    def vocal(self, destinataire: str, opus: bytes) -> None:
        """Note vocale (0029). Erreur relancée sans l'adresse, qui contient le jeton du bot."""
        try:
            with self._client() as h:
                h.post(f"https://api.telegram.org/bot{self._jeton()}/sendVoice", data={"chat_id": destinataire},
                       files={"voice": ("reponse.ogg", opus, "audio/ogg")}).raise_for_status()
        except httpx.HTTPError as e:
            raise ErreurTelegram(f"Telegram sendVoice : {type(e).__name__}") from None

    def media(self, contenu: Contenu) -> bytes:
        chemin = self._appel("getFile", {"file_id": contenu.media}).get("file_path", "")
        try:
            with self._client() as h:
                return telecharger(h, f"https://api.telegram.org/file/bot{self._jeton()}/{chemin}")
        except httpx.HTTPError as e:
            raise ErreurTelegram(f"Telegram fichier : {type(e).__name__}") from None


class CanalTelegram:
    nom = "telegram"

    def __init__(self, envoyeur: ClientTelegram | None = None):
        self.envoyeur = envoyeur or ClientTelegram()

    def lire(self, payload: dict) -> list[Entrant]:
        return lire(payload)

    def traiter(self, entrant: Entrant, services: Services) -> None:
        traiter(entrant, services, self.envoyeur)


CANAL = CanalTelegram()
