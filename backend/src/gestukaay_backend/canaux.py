"""Frontière entre les webhooks (SAN, webhooks.py) et le module de canal (KBD), pour WhatsApp et Telegram.

Répartition (décision de KBD, à venir) :
  - SAN : routes, vérification de Meta / Telegram, 200 immédiat et traitement en tâche de fond, unicité
    par identifiant de message, numéro haché et contexte de suivi comme pour le web ;
  - KBD : un module de canal, en fonctions pures, que les routes appellent : lire le payload, interpréter
    (question, choix « 1 » / « benn », commandes), formater la réponse et l'envoyer (Graph API, Bot API).

Le module de KBD fournit, pour chaque canal, un objet conforme à `Canal`. Le backend lui donne des
`Services` qui passent par le même chemin que le web (/v1/ask, /v1/ask/{id}/confirm) : suivi sur trois
échanges, journal, réponse gardée pour son adresse /r/{id}. Le numéro ne quitte jamais `Entrant.expediteur` :
il devient `conversation_id`, haché par le stockage avant d'être écrit (contrat-v1 §5, page Confidentialité).
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from gestukaay_contracts.models import AskResponse, TranscriptionResponse
from gestukaay_engine import NoteVocale

NomCanal = Literal["whatsapp", "telegram"]


@dataclass(frozen=True)
class Entrant:
    """Un message reçu. Le backend n'utilise que `message_id` (unicité) et `expediteur` (conversation) ;
    `contenu` appartient au module de canal, qui le retrouve dans traiter()."""

    message_id: str  # WhatsApp : wamid… ; Telegram : update_id
    expediteur: str  # numéro WhatsApp ou chat_id Telegram : jamais journalisé tel quel
    contenu: Any = None


@dataclass
class Services:
    """Ce que le backend met à disposition du module de canal, pour une conversation."""

    conversation_id: str  # « whatsapp:<numéro> », haché avant toute écriture
    demander: Callable[..., AskResponse]  # (question, *, langue, source, transcription_brute, audio_retour)
    confirmer: Callable[[str, str], AskResponse]  # (reponse_id, choix_id) : « 1 », « benn »
    derniere: Callable[[], AskResponse | None]  # dernière réponse de la conversation (choix numérotés)
    transcrire: Callable[[bytes, str], TranscriptionResponse]  # (audio, "ogg") pour les notes vocales
    # Réponse dite en wolof (#29, décision 0029) : lente, appelée après l'envoi du texte ; None = texte seul
    parler: Callable[[AskResponse], NoteVocale | None] = field(default=lambda rep: None)


class Canal(Protocol):
    nom: NomCanal

    def lire(self, payload: dict) -> list[Entrant]:
        """Les messages à traiter du payload. Les statuts (envoyé, lu…) ne donnent rien."""
        ...

    def traiter(self, entrant: Entrant, services: Services) -> None:
        """Interpréter, appeler les services, formater et envoyer la réponse. Appelé en tâche de fond."""
        ...


def charger_canaux() -> dict[str, Canal]:
    """Les canaux du module de KBD (`gestukaay_canaux.whatsapp`, `gestukaay_canaux.telegram`), s'il est
    installé. Sans lui, les webhooks répondent 404 : rien n'est reçu tant que rien ne sait répondre."""
    canaux: dict[str, Canal] = {}
    for nom in ("whatsapp", "telegram"):
        try:
            module = importlib.import_module(f"gestukaay_canaux.{nom}")
        except ModuleNotFoundError:
            continue
        canaux[nom] = module.CANAL
    return canaux
