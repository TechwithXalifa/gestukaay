"""Accès du moteur au socle extrait (issue #11).

Le socle extrait (#4) est un dossier hors Git : observations.csv, sources.csv
(défaut ../socle_gestukaay, variable GESTUKAAY_SOCLE_EXTRAIT). Il est chargé
une fois en mémoire et indexé par indicateur : une réponse prend quelques
millisecondes.

Seule `charger()` connaît le format de stockage : si le socle passe dans
PostgreSQL (#8, avec SAN), c'est la seule fonction à réécrire.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class Observation:
    id: str
    indicateur: str
    zone: str
    zone_presumee: bool
    periode: str
    desagregation: tuple[tuple[str, str], ...]  # trié, hors zone et hors indicateur
    valeur: float
    unite: str
    echelle: str
    source_id: str
    nature: str
    base_projection: str

    def dims(self) -> dict[str, str]:
        return dict(self.desagregation)


@dataclass(frozen=True)
class SourceJeu:
    id: str
    producteur: str
    organisme: str
    titre: str
    date_publication: date | None
    licence: str
    url: str
    derniere_maj: date | None = None  # #233 : dernière mise à jour du jeu (séries mensuelles, trimestrielles…)


class Socle:
    def __init__(self, observations: list[Observation], sources: dict[str, SourceJeu], version: str = "dev"):
        self.version = version
        self.sources = sources
        self._par_indicateur: dict[str, list[Observation]] = defaultdict(list)
        for o in observations:
            self._par_indicateur[o.indicateur].append(o)

    def observations(self, indicateur: str) -> list[Observation]:
        return self._par_indicateur.get(indicateur, [])

    def __len__(self) -> int:
        return sum(len(v) for v in self._par_indicateur.values())


def _date(texte: str) -> date | None:
    try:
        return date.fromisoformat(texte[:10])
    except ValueError:
        return None


def charger(dossier: Path) -> Socle:
    """Lit le socle extrait (CSV). Seule fonction liée au format de stockage."""
    csv.field_size_limit(2**31 - 1)  # sys.maxsize déborde sous Windows (long C sur 32 bits)
    i = sys.intern  # mêmes codes, unités et libellés répétés des centaines de milliers de fois
    desags: dict[str, tuple] = {}
    observations = []
    with open(dossier / "observations.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            brut = r["desagregation"] or "{}"
            if brut not in desags:
                desags[brut] = tuple(sorted((i(k), i(v)) for k, v in json.loads(brut).items()))
            observations.append(Observation(
                id=r["observation_id"], indicateur=i(r["indicateur"]), zone=i(r["zone"]),
                zone_presumee=r["zone_presumee"] == "oui", periode=i(r["periode"]), desagregation=desags[brut],
                valeur=float(r["valeur"]), unite=i(r["unite"]), echelle=i(r["echelle"]), source_id=i(r["source_id"]),
                nature=i(r.get("nature") or "observee"), base_projection=i(r.get("base_projection") or ""),
            ))
    with open(dossier / "sources.csv", encoding="utf-8", newline="") as f:
        sources = {r["source_id"]: SourceJeu(r["source_id"], r["producteur"], r["organisme"], r["titre"],
                                             _date(r["date_publication"]), r["licence"], r["url"],
                                             _date(r.get("derniere_maj") or ""))
                   for r in csv.DictReader(f, delimiter=";")}
    version_ = dossier / "VERSION"
    return Socle(observations, sources, version_.read_text().strip() if version_.exists() else "dev")


class SocleIncoherent(RuntimeError):
    """Le socle cite des indicateurs que le référentiel ne connaît pas : ne pas démarrer."""


def verifier(s: Socle) -> None:
    """Chaque indicateur du socle doit exister dans le référentiel du dépôt (décision 0013).
    Sinon le moteur refuse de démarrer plutôt que de répondre avec des codes orphelins."""
    from gestukaay_socle.indicateurs import indicateurs

    inconnus = sorted(set(s._par_indicateur) - indicateurs().keys())
    if inconnus:
        raise SocleIncoherent(
            f"socle {s.version} : {len(inconnus)} indicateurs absents du référentiel "
            f"(ex. {', '.join(inconnus[:3])}) : régénérer le socle avec les référentiels actuels")


@cache
def socle() -> Socle:
    """Le socle de $GESTUKAAY_SOCLE_EXTRAIT : un dossier de version, ou le dossier qui les contient
    (la version publiée la plus récente est prise). Vérifié avant d'être servi."""
    from gestukaay_socle.version import dossier_du_socle, ecarts_referentiels

    chemin = Path(os.environ.get("GESTUKAAY_SOCLE_EXTRAIT", RACINE.parent / "socle_gestukaay"))
    if not chemin.is_absolute():
        chemin = (RACINE / chemin).resolve()
    dossier = dossier_du_socle(chemin)
    s = charger(dossier)
    verifier(s)
    if ecarts := ecarts_referentiels(dossier):
        print(f"[socle {s.version}] référentiels modifiés depuis l'extraction : {', '.join(ecarts)}",
              file=sys.stderr)
    return s
