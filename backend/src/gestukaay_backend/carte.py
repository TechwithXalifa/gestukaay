"""Carte des 14 régions (Explorer, vue « Carte »).

Une valeur par région pour UNE période commune, colorée du plus clair au plus foncé : les comparaisons
régionales (pauvreté, chômage, population…) deviennent visibles d'un coup d'œil. Rien n'est calculé : chaque
valeur est celle que servirait Explorer (moteur.series), à la période choisie. Une région qui ne publie pas cette
période est signalée, jamais estimée.

Le contrat des séries limite un appel à 6 zones : les 14 régions sont lues en trois appels, sans toucher au moteur.
"""

from __future__ import annotations

from collections import Counter

from gestukaay_contracts.models import RefIndicateur, RefZone, Source
from gestukaay_socle.zones import zones
from pydantic import BaseModel

PAR_APPEL = 6  # SeriesResponse.series : 6 zones au plus
# Période par défaut : la plus récente publiée par au moins les trois quarts des régions de la meilleure période
# (sinon une seule région publiée en 2025 l'emporterait sur les quatorze de 2023)
PART_MIN = 0.75


class ValeurZone(BaseModel):
    region: str  # la tuile : la région elle-même, ou celle d'une académie (données d'éducation, 0003)
    zone: RefZone  # la zone servie, telle que le moteur la nomme (« académie de Kolda »)
    valeur: float
    valeur_affichee: str
    nature: str | None = None  # « projection », « estimation » : étiquetées sur la carte comme partout


class CarteResponse(BaseModel):
    version_socle: str
    indicateur: RefIndicateur
    unite: str
    periode: str | None  # None : aucune région ne publie cet indicateur
    libelle_periode: str | None
    periodes: list[str]  # publiées par au moins une région, la plus récente d'abord
    valeurs: list[ValeurZone]  # régions qui publient la période, de la plus haute à la plus basse
    absents: list[str]  # régions sans valeur à cette période
    ensemble: ValeurZone | None  # le Sénégal à la même période, s'il est publié
    sources: list[Source]


def regions() -> list[str]:
    return sorted(z.code for z in zones().values() if z.niveau == "region")


def _region(zone: RefZone) -> str:
    """Une académie se place sur sa région (référentiel des zones, colonne parent)."""
    z = zones().get(zone.code)
    return z.parent if z and z.niveau == "academie" and z.parent else zone.code


def _lire(moteur, indicateur: str, codes: list[str]):
    series, version, ref, unite = [], "", None, ""
    for i in range(0, len(codes), PAR_APPEL):
        r = moteur.series(indicateur, codes[i:i + PAR_APPEL])
        series += r.series
        version, ref, unite = r.version_socle, r.indicateur, r.unite
    return series, version, ref, unite


def carte(moteur, indicateur: str, periode: str | None = None) -> CarteResponse:
    toutes = regions()
    series, version, ref, unite = _lire(moteur, indicateur, [*toutes, "SN"])
    par_region = [s for s in series if s.zone.code != "SN"]
    pays = next((s for s in series if s.zone.code == "SN"), None)
    compte = Counter(p.periode for s in par_region for p in s.points)
    if periode is None and compte:
        meilleur = max(compte.values())
        periode = max(p for p, n in compte.items() if n >= meilleur * PART_MIN)
    valeurs, libelle, sources = [], None, {}
    for s in par_region:
        point = next((p for p in s.points if p.periode == periode), None)
        if point is None:
            continue
        libelle = point.libelle
        sources.setdefault(s.source.url, s.source)
        valeurs.append(ValeurZone(region=_region(s.zone), zone=s.zone, valeur=point.valeur,
                                  valeur_affichee=point.valeur_affichee, nature=point.nature))
    ensemble = None
    if pays and (point := next((p for p in pays.points if p.periode == periode), None)):
        ensemble = ValeurZone(region="SN", zone=pays.zone, valeur=point.valeur,
                              valeur_affichee=point.valeur_affichee, nature=point.nature)
        libelle = libelle or point.libelle
    publiees = {v.region for v in valeurs}
    return CarteResponse(
        version_socle=version, indicateur=ref, unite=unite, periode=periode if compte else None,
        libelle_periode=libelle, periodes=sorted(compte, reverse=True),
        valeurs=sorted(valeurs, key=lambda v: -v.valeur), absents=[c for c in toutes if c not in publiees],
        ensemble=ensemble, sources=list(sources.values()),
    )
