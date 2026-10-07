"""Frontière entre le moteur (KBD) et le backend (SAN).

Le backend ne connaît que ce Protocol. Il obtient une implémentation par
charger_moteur(), qui lit la variable d'environnement GESTUKAAY_MOTEUR :
  - "fake" (défaut tant que le vrai moteur n'est pas livré) : réponses
    fixes issues de contracts/examples/, pour développer le web et l'API ;
  - "reel" : le moteur branché sur le socle et le LLM.

Le moteur est sans état : il ne stocke rien. La persistance (réponses,
journal, feedback) et les URL relèvent du backend.

Une fonction pas encore construite dans le moteur réel lève NonDisponible :
le backend la rend en 503 plutôt que de servir des chiffres du faux moteur.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from gestukaay_contracts.models import (
    AskRequest,
    AskResponse,
    CatalogueResponse,
    FicheIndicateur,
    RequeteStructuree,
    SeriesResponse,
    SituateRequest,
    SituateResponse,
    TranscriptionResponse,
)


class NonDisponible(RuntimeError):
    """Fonction pas encore construite dans le moteur réel (voix #28, « Où je me situe » #95)."""


class SaisieInvalide(ValueError):
    """Saisie hors du référentiel (« Où je me situe » : région inconnue) : le backend rend 422."""


class IndicateurInconnu(LookupError):
    """Code d'indicateur absent du référentiel ou sans valeur dans le socle : le backend rend 404."""


@dataclass(frozen=True)
class NoteVocale:
    """Réponse dite en wolof (#29, #30, décision 0029) : OGG/Opus, 60 Ko au plus."""

    opus: bytes
    duree_s: float
    voix: str  # « oolel » ou « adia » (repli)
    texte: str = ""  # ce que la note dit (revue #136 : affiché sous le lecteur, cahier 7.5 et 9.7)


class Moteur(Protocol):
    def repondre(self, req: AskRequest, contexte: list[RequeteStructuree | None] | None = None) -> AskResponse:
        """Question -> réponse (exacte, approchée ou aucune) [EF-05].

        contexte : les requêtes structurées des 3 derniers échanges de la
        conversation, du plus ancien au plus récent, conservées par le backend, pour
        « et Kaolack ? » [EF-09] ; None pour un échange sans requête (incompréhension).
        Le moteur repart du dernier échange compris (décision 0021).
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

    # v1.4.0 — Catalogue, fiche et séries d'Explorer (décision 0023). Lecture seule, sans LLM.
    def catalogue(self, domaine: str | None = None, q: str | None = None, niveau: str | None = None,
                  limite: int = 50, decalage: int = 0) -> CatalogueResponse:
        """Indicateurs qui ont des valeurs, filtrés, vérifiés d'abord puis par libellé."""
        ...

    def fiche(self, code: str) -> FicheIndicateur:
        """Fiche d'un indicateur ; IndicateurInconnu si le code n'existe pas."""
        ...

    def series(self, indicateur: str, zones: list[str], debut: str | None = None,
               fin: str | None = None) -> SeriesResponse:
        """Séries publiées d'un indicateur pour 1 à 6 zones, sans interpolation ; IndicateurInconnu
        si le code n'existe pas. Une zone sans valeur sur la période va dans `absents`."""
        ...

    def parler(self, rep: AskResponse) -> NoteVocale | None:
        """La réponse dite en wolof, ou None : le texte part seul (#29, décision 0029). Lent (la voix
        se calcule, environ la durée de la note sur un Mac) : à appeler après l'envoi du texte."""
        ...

    def version_socle(self) -> str: ...


def charger_moteur() -> Moteur:
    choix = os.environ.get("GESTUKAAY_MOTEUR", "fake")
    if choix == "fake":
        from .fake import MoteurFactice

        return MoteurFactice()
    if choix == "reel":
        from .moteur import MoteurReel

        return MoteurReel()
    raise ValueError(f"GESTUKAAY_MOTEUR inconnu : {choix!r}")
