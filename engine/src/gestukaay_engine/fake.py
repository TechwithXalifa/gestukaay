"""Moteur factice : renvoie les exemples du contrat selon des mots-clés.

Permet au backend et au web d'avancer sans attendre le moteur réel.
Questions reconnues (insensible à la casse) :
  « wolof » / « ñaata » -> exacte_wolof_vocal
  « et »  + deux villes -> exacte_comparaison     (ex. « Dakar et Thiès »)
  « ville »             -> approchee
  « 2035 »              -> exacte_projection (badge « projection »)
  « 2040 » / « 2050 »   -> aucune_projection
  « sérère » / « sereer » -> aucune_hors_socle
  « thiès » / « thies » -> exacte_valeur
  sinon                 -> aucune_incomprehension
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from gestukaay_contracts.models import (
    AskRequest,
    AskResponse,
    RequeteStructuree,
    SituateRequest,
    SituateResponse,
    TranscriptionResponse,
)

EXEMPLES = Path(__file__).resolve().parents[3] / "contracts" / "examples"


def _charger(nom: str, question: str) -> AskResponse:
    rep = AskResponse.model_validate_json((EXEMPLES / f"{nom}.json").read_text(encoding="utf-8"))
    ident = uuid.uuid4().hex[:12]
    rep.reponse.id = ident
    rep.reponse.url = f"https://app.gestukaay.test/r/{ident}"
    rep.reponse.question = question
    rep.reponse.cree_le = datetime.now(UTC)
    return rep


class MoteurFactice:
    def repondre(self, req: AskRequest, contexte: list[RequeteStructuree] | None = None) -> AskResponse:
        q = req.question.lower()
        if "ñaata" in q or "naata" in q or req.langue == "wo":
            nom = "exacte_wolof_vocal"
        elif " et " in q and ("dakar" in q or "thi" in q):
            nom = "exacte_comparaison"
        elif "ville" in q:
            nom = "approchee"
        elif "2035" in q:
            nom = "exacte_projection"
        elif "2040" in q or "2050" in q:
            nom = "aucune_projection"
        elif "sérère" in q or "serere" in q or "sereer" in q:
            nom = "aucune_hors_socle"
        elif "thiès" in q or "thies" in q:
            nom = "exacte_valeur"
        else:
            nom = "aucune_incomprehension"
        return _charger(nom, req.question)

    def executer(self, requete: RequeteStructuree, question: str, langue: str) -> AskResponse:
        return _charger("exacte_valeur", question)

    def transcrire(self, audio: bytes, format_audio: str, langue: str = "auto") -> TranscriptionResponse:
        return TranscriptionResponse.model_validate_json((EXEMPLES / "transcription.json").read_text(encoding="utf-8"))

    def situer(self, req: SituateRequest) -> SituateResponse:
        # Toujours l'exemple de Kolda, quelle que soit la saisie (faux moteur)
        return SituateResponse.model_validate_json((EXEMPLES / "situer.json").read_text(encoding="utf-8"))

    def version_socle(self) -> str:
        return "fake"
