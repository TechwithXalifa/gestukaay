"""Canal WhatsApp (Cloud API, Graph v25.0) : #31 à #34, décision 0025.

Configuration (`.env`, jamais dans Git) : WHATSAPP_TOKEN (jeton d'utilisateur système, sans
expiration), WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_API_VERSION (défaut v25.0). La signature et l'unicité
des messages sont vérifiées par le backend avant d'arriver ici.
"""

from __future__ import annotations

import logging
import os

import httpx
from gestukaay_backend.canaux import Entrant, Services
from gestukaay_contracts.models import Choix

from .conversation import Contenu, traiter
from .media import relance, telecharger
from .textes import bouton_liste, texte

_log = logging.getLogger("gestukaay.canaux.whatsapp")
VERSION = "v25.0"
DELAI_S = 10


def lire(payload: dict) -> list[Entrant]:
    """Les messages du payload ; les statuts (envoyé, lu…) ne donnent rien, sauf un échec, journalisé
    sans le numéro (essai du 07/10 : envois acceptés par l'API mais jamais remis)."""
    out = []
    for entree in payload.get("entry", []):
        for changement in entree.get("changes", []):
            valeur = changement.get("value", {})
            for m in valeur.get("messages", []) or []:
                out.append(Entrant(m["id"], m["from"], _contenu(m)))
            for st in valeur.get("statuses", []) or []:  # un envoi accepté peut échouer ensuite : on le dit
                if st.get("status") == "failed":
                    raisons = "; ".join(f"code {e.get('code')} : {e.get('title', '')} {(e.get('error_data') or {}).get('details', '')}".strip()
                                        for e in st.get("errors", []) or [])
                    _log.warning("whatsapp : message non remis (%s)", raisons or "sans raison donnée")
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




def _raison_meta(r: httpx.Response) -> str:
    """Code et message d'erreur de l'API Graph, sans le corps envoyé ni le numéro du destinataire."""
    try:
        corps = r.json()
    except ValueError:
        return f"HTTP {r.status_code}"
    # un corps inattendu (liste, chaîne, {"error": "…"} d'un proxy) ne doit pas cacher l'erreur HTTP (revue de SAN)
    e = corps.get("error") if isinstance(corps, dict) else None
    if not isinstance(e, dict):
        return f"HTTP {r.status_code}"
    details = e.get("error_data") or {}
    details = details.get("details", "") if isinstance(details, dict) else ""
    return f"HTTP {r.status_code}, code {e.get('code')} : {e.get('message', '')} {details}".strip()

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
                            headers={"Authorization": f"Bearer {jeton}"}, transport=self._transport,
                            mounts=relance(self._transport))

    def _envoyer(self, corps: dict) -> None:
        with self._http() as h:
            r = h.post(f"/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages",
                       json={"messaging_product": "whatsapp", **corps})
        if r.is_error:  # la raison donnée par Meta (code 131030 : destinataire hors de la liste de test…),
            _log.warning("whatsapp : envoi refusé (%s)", _raison_meta(r))  # jamais le numéro ni le texte
        r.raise_for_status()

    def accuser(self, destinataire: str, contenu: Contenu) -> None:
        """Lu (coches bleues) et « en train d'écrire » jusqu'à la réponse (#32)."""
        if contenu.accuse:
            self._envoyer({"status": "read", "message_id": contenu.accuse,
                           "typing_indicator": {"type": "text"}})

    def texte(self, destinataire: str, message: str) -> None:
        self._envoyer({"recipient_type": "individual", "to": destinataire, "type": "text",
                       "text": {"preview_url": False, "body": message[:4096]}})

    def choix(self, destinataire: str, choix: list[Choix], message: str) -> None:
        """La liste à toucher (#34), avec le texte de la réponse comme corps du même message (#213) ; au-delà
        de 1 024 caractères (limite de Meta), le texte part d'abord, seul."""
        if len(message) > 1024:
            self.texte(destinataire, message)
            message = texte("choisir")
        lignes = [{"id": f"choix-{c.id}", "title": f"{c.id}. {c.libelle}"[:24],
                   "description": c.libelle[:72]} for c in choix]
        self._envoyer({"recipient_type": "individual", "to": destinataire, "type": "interactive",
                       "interactive": {"type": "list", "body": {"text": message[:1024]},
                                       "action": {"button": bouton_liste(),
                                                  "sections": [{"title": "Choix", "rows": lignes}]}}})

    def preparer_vocal(self, destinataire: str) -> None:
        pass  # l'API Cloud n'a pas d'indicateur « enregistre un audio »

    def vocal(self, destinataire: str, opus: bytes) -> None:
        """Note vocale (0029) : le fichier est déposé chez Meta, puis envoyé comme message vocal."""
        with self._http() as h:
            r = h.post(f"/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/media",
                       data={"messaging_product": "whatsapp", "type": "audio/ogg"},
                       files={"file": ("reponse.ogg", opus, "audio/ogg")})
            ident = r.raise_for_status().json()["id"]
        self._envoyer({"recipient_type": "individual", "to": destinataire, "type": "audio",
                       "audio": {"id": ident, "voice": True}})

    def media(self, contenu: Contenu) -> bytes:
        """Note vocale : l'adresse du média, puis son contenu (en mémoire seulement, 2 Mo au plus)."""
        with self._http() as h:
            url = h.get(f"/{contenu.media}").raise_for_status().json()["url"]
            return telecharger(h, url)


class CanalWhatsApp:
    nom = "whatsapp"

    def __init__(self, envoyeur: ClientGraph | None = None):
        self.envoyeur = envoyeur or ClientGraph()

    def lire(self, payload: dict) -> list[Entrant]:
        return lire(payload)

    def traiter(self, entrant: Entrant, services: Services) -> None:
        traiter(entrant, services, self.envoyeur)


CANAL = CanalWhatsApp()
