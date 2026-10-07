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
    CatalogueResponse,
    FicheIndicateur,
    Graphique,
    PointGraphique,
    RequeteStructuree,
    SerieGraphique,
    SeriesResponse,
    SituateRequest,
    SituateResponse,
    TranscriptionResponse,
)
from gestukaay_socle.zones import normaliser

from .interface import IndicateurInconnu

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
    def repondre(self, req: AskRequest, contexte: list[RequeteStructuree | None] | None = None) -> AskResponse:
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

    def parler(self, rep: AskResponse) -> None:
        return None  # pas de voix dans le faux moteur : le texte part seul

    def situer(self, req: SituateRequest) -> SituateResponse:
        # Toujours l'exemple de Kolda, quelle que soit la saisie (faux moteur)
        return SituateResponse.model_validate_json((EXEMPLES / "situer.json").read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # v1.4.0 (décision 0023) : catalogue, fiche et séries, sur les exemples du contrat.
    # Seul le taux de pauvreté a une fiche et des séries ; un autre code -> IndicateurInconnu (404).
    # ------------------------------------------------------------------

    def catalogue(self, domaine: str | None = None, q: str | None = None, niveau: str | None = None,
                  limite: int = 50, decalage: int = 0) -> CatalogueResponse:
        rep = CatalogueResponse.model_validate_json((EXEMPLES / "catalogue.json").read_text(encoding="utf-8"))
        if not (domaine or q or niveau):
            rep.indicateurs = rep.indicateurs[decalage:decalage + limite]
            return rep
        garder = [i for i in rep.indicateurs
                  if (not domaine or normaliser(i.domaine) == normaliser(domaine))
                  and (not q or normaliser(q) in normaliser(f"{i.libelle} {i.operation} {i.producteur}"))
                  and (not niveau or niveau in i.niveaux)]
        rep.total = len(garder)
        rep.indicateurs = garder[decalage:decalage + limite]
        return rep

    def fiche(self, code: str) -> FicheIndicateur:
        rep = FicheIndicateur.model_validate_json((EXEMPLES / "fiche_indicateur.json").read_text(encoding="utf-8"))
        if code != rep.indicateur.code:
            raise IndicateurInconnu(code)
        return rep

    def series(self, indicateur: str, zones: list[str], debut: str | None = None,
               fin: str | None = None) -> SeriesResponse:
        rep = SeriesResponse.model_validate_json((EXEMPLES / "series.json").read_text(encoding="utf-8"))
        if indicateur != rep.indicateur.code:
            raise IndicateurInconnu(indicateur)
        par_zone = {s.zone.code: s for s in rep.series}
        series, absents = [], []
        for z in zones:
            s = par_zone.get(z)
            points = [p for p in (s.points if s else [])
                      if (not debut or p.periode >= debut) and (not fin or p.periode <= fin)]
            if s and points:
                series.append(s.model_copy(update={"points": points}))
            else:
                absents.append(z)
        periodes = sorted({p.periode for s in series for p in s.points})
        graphique = None
        if series:
            courbe = len(periodes) > 1
            graphique = Graphique(
                type="courbe" if courbe else "barres_horizontales",
                titre=f"{rep.indicateur.libelle} {f'de {periodes[0]} à {periodes[-1]}' if courbe else f'en {periodes[0]}'}"
                      f" ({rep.unite})",
                unite=rep.unite,
                series=[SerieGraphique(nom=s.zone.libelle, points=[PointGraphique(x=p.periode, y=p.valeur)
                                                                  for p in s.points]) for s in series]
                if courbe else [SerieGraphique(nom=rep.indicateur.libelle, points=sorted(
                    (PointGraphique(x=s.zone.libelle, y=s.points[0].valeur) for s in series),
                    key=lambda p: -p.y))],
                pied=rep.graphique.pied if rep.graphique else "",
            )
        return rep.model_copy(update={"series": series, "absents": absents, "graphique": graphique})

    def version_socle(self) -> str:
        return "fake"
