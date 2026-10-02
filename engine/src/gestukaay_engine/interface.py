"""Frontière entre le moteur (KBD) et le backend (SAN).

Le backend ne connaît que ce Protocol. Il obtient une implémentation par
charger_moteur(), qui lit la variable d'environnement GESTUKAAY_MOTEUR :
  - "fake" (défaut tant que le vrai moteur n'est pas livré) : réponses
    fixes issues de contracts/examples/, pour développer le web et l'API ;
  - "reel" : le moteur branché sur le socle et le LLM.

Le moteur est sans état : il ne stocke rien. La persistance (réponses,
journal, feedback) et les URL relèvent du backend.
"""

from __future__ import annotations

import os
from typing import Protocol

from gestukaay_contracts.models import (
    AskRequest,
    AskResponse,
    RequeteStructuree,
    SituateRequest,
    SituateResponse,
    TranscriptionResponse,
)


class Moteur(Protocol):
    def repondre(self, req: AskRequest, contexte: list[RequeteStructuree] | None = None) -> AskResponse:
        """Question -> réponse (exacte, approchée ou aucune) [EF-05].

        contexte : les requêtes structurées des 3 derniers échanges de la
        conversation, conservées par le backend, pour « et Kaolack ? » [EF-09].
        """
        ...

    def executer(self, requete: RequeteStructuree, question: str, langue: str) -> AskResponse:
        """Exécute une requête déjà structurée, sans LLM.

        Utilisé pour confirmer un choix d'une réponse approchée : le backend
        renvoie la `requete` du `Choix` sélectionné [EF-06, US-13].
        """
        ...

    def transcrire(self, audio: bytes, format_audio: str, langue: str = "auto") -> TranscriptionResponse:
        """Audio (webm/ogg Opus, 60 s max) -> texte, sans répondre (v1.1.0, décision 0004 §1).
        Le web affiche le texte, l'utilisateur le corrige, puis appelle repondre()."""
        ...

    def situer(self, req: SituateRequest) -> SituateResponse:
        """« Où je me situe » : comparaison aux moyennes publiées (v1.1.0, décision 0004 §2).
        Ne conserve RIEN de ce qui est saisi [EF-40]."""
        ...

    def version_socle(self) -> str: ...


def charger_moteur() -> Moteur:
    choix = os.environ.get("GESTUKAAY_MOTEUR", "fake")
    if choix == "fake":
        from .fake import MoteurFactice

        return MoteurFactice()
    if choix == "reel":
        raise NotImplementedError("Moteur réel en cours de construction (KBD).")
    raise ValueError(f"GESTUKAAY_MOTEUR inconnu : {choix!r}")
