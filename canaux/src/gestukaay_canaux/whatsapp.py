"""Canal WhatsApp (Cloud API, Graph v25.0) : #31 à #34, décision 0025.

Configuration (`.env`, jamais dans Git) : WHATSAPP_TOKEN (jeton d'utilisateur système, sans
expiration), WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_API_VERSION (défaut v25.0). La signature et l'unicité
des messages sont vérifiées par le backend avant d'arriver ici.
"""

from __future__ import annotations

import os

import httpx
from gestukaay_backend.canaux import Entrant, Services
from gestukaay_contracts.models import Choix

from .conversation import Contenu, traiter
from .textes import bouton_liste, texte

VERSION = "v25.0"
DELAI_S = 10


def lire(payload: dict) -> list[Entrant]:
    """Les messages du payload ; les statuts (envoyé, lu…) ne donnent rien."""
    out = []
    for entree in payload.get("entry", []):
        for changement in entree.get("changes", []):
            for m in changement.get("value", {}).get("messages", []) or []:
                out.append(Entrant(m["id"], m["from"], _contenu(m)))
    return out


def _contenu(m: dict) -> Contenu:
    t, accuse = m.get("type"), m["id"]
    if t == "text":
        return Contenu("texte", texte=m.get("text", {}).get("body", ""), accuse=accuse)
    if t == "audio":
        return Contenu("audio", media=m.get("audio", {}).get("id", ""), accuse=accuse)
    if t == "interactive":
        i = m.get("interactive", {})
        reponse = i.get("list_reply") or i.get("button_reply") or {}
        ident = reponse.get("id", "")
        if ident.startswith("choix-"):
            return Contenu("choix", choix_id=ident.removeprefix("choix-"), accuse=accuse)
    if t == "button":  # bouton d'un modèle de message
        return Contenu("texte", texte=m.get("button", {}).get("text", ""), accuse=accuse)
    return Contenu("autre", accuse=accuse)


class ClientGraph:
    """Envoi par l'API Graph. Le jeton est dans l'en-tête, jamais dans l'adresse ni les journaux."""

    gras = True

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def _http(self) -> httpx.Client:
        jeton = os.environ.get("WHATSAPP_TOKEN", "")
        if not jeton or not os.environ.get("WHATSAPP_PHONE_NUMBER_ID"):
            raise RuntimeError("WHATSAPP_TOKEN ou WHATSAPP_PHONE_NUMBER_ID absent de l'environnement")
        version = os.environ.get("WHATSAPP_API_VERSION", VERSION)
        return httpx.Client(base_url=f"https://graph.facebook.com/{version}", timeout=DELAI_S,
                            headers={"Authorization": f"Bearer {jeton}"}, transport=self._transport)

    def _envoyer(self, corps: dict) -> None:
        with self._http() as h:
            h.post(f"/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages",
                   json={"messaging_product": "whatsapp", **corps}).raise_for_status()

    def accuser(self, destinataire: str, contenu: Contenu) -> None:
        """Lu (coches bleues) et « en train d'écrire » jusqu'à la réponse (#32)."""
        if contenu.accuse:
            self._envoyer({"status": "read", "message_id": contenu.accuse,
                           "typing_indicator": {"type": "text"}})

    def texte(self, destinataire: str, message: str) -> None:
        self._envoyer({"recipient_type": "individual", "to": destinataire, "type": "text",
                       "text": {"preview_url": False, "body": message[:4096]}})

    def choix(self, destinataire: str, choix: list[Choix]) -> None:
        """La liste à toucher (#34) ; les choix sont aussi numérotés dans le texte qui précède."""
        lignes = [{"id": f"choix-{c.id}", "title": f"{c.id}. {c.libelle}"[:24],
                   "description": c.libelle[:72]} for c in choix]
        self._envoyer({"recipient_type": "individual", "to": destinataire, "type": "interactive",
                       "interactive": {"type": "list", "body": {"text": texte("choisir")[:1024]},
                                       "action": {"button": bouton_liste(),
                                                  "sections": [{"title": "Choix", "rows": lignes}]}}})

    def media(self, contenu: Contenu) -> bytes:
        """Note vocale : l'adresse du média, puis son contenu (en mémoire seulement)."""
        with self._http() as h:
            url = h.get(f"/{contenu.media}").raise_for_status().json()["url"]
            return h.get(url).raise_for_status().content


class CanalWhatsApp:
    nom = "whatsapp"

    def __init__(self, envoyeur: ClientGraph | None = None):
        self.envoyeur = envoyeur or ClientGraph()

    def lire(self, payload: dict) -> list[Entrant]:
        return lire(payload)

    def traiter(self, entrant: Entrant, services: Services) -> None:
        traiter(entrant, services, self.envoyeur)


CANAL = CanalWhatsApp()
