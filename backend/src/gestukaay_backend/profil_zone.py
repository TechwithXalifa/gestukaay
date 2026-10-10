"""« Ma région en chiffres » : les chiffres clés d'une zone, et la comparaison de deux zones.

Répond aux « parle-moi de Matam » : une douzaine d'indicateurs choisis (population, pauvreté, emploi, école,
santé, logement), chacun avec sa dernière valeur publiée pour la zone, sa période et sa source. Pour une région,
son rang parmi les régions qui publient la même période (un tri des valeurs publiées, rien de calculé).

Rien n'est inventé ni modifié : chaque valeur est celle que servirait Explorer (moteur.series), jamais une
projection future (décision 0035, comme la fiche indicateur). Un indicateur que la zone ne publie pas est listé
dans `absents`, jamais estimé.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from gestukaay_contracts.models import RefIndicateur, RefZone, Source
from gestukaay_engine import IndicateurInconnu
from gestukaay_socle.zones import zones
from pydantic import BaseModel

from .carte import carte

NIVEAUX = ("pays", "region")  # un département ne publie presque aucun de ces indicateurs (Mbour : aucun)


@dataclass(frozen=True)
class ChiffreCle:
    theme: str
    code: str


# Indicateurs publiés pour les 14 régions et le Sénégal (vérifiés sur le socle 2026.10 le 10/10), vérifiés d'abord
CHIFFRES_CLES = (
    ChiffreCle("Population", "pvswjnd"),
    ChiffreCle("Population", "rfegvpb.taux-durbanisation"),
    ChiffreCle("Population", "elwxsmc.indice-synthetique-de-fecondite"),
    ChiffreCle("Niveau de vie", "jcvcajc.taux-de-pauvrete"),
    ChiffreCle("Niveau de vie", "jcvcajc.total"),
    ChiffreCle("Niveau de vie", "qjyrtof.gini"),
    ChiffreCle("Emploi", "dwibrlf"),
    ChiffreCle("Éducation", "ervtjfc.taux-brut-de-scolarisation"),
    ChiffreCle("Santé", "wdvdnub.proportion-denfants-de-12-a-23-mois"),
    ChiffreCle("Santé", "smcofug.quotient-de-mortalite-infanto-juvenile"),
    ChiffreCle("Logement et services", "kdtstle.robinet-dans-logement-concession"),
    ChiffreCle("Logement et services", "vlaobkb"),
)


class ValeurCle(BaseModel):
    theme: str
    indicateur: RefIndicateur
    unite: str
    zone_servie: RefZone  # « académie de Kolda » pour l'école : la zone telle que le moteur la nomme
    periode: str
    libelle_periode: str
    valeur: float
    valeur_affichee: str
    nature: str | None = None
    rang: int | None = None  # 1 = la valeur la plus élevée, parmi les régions qui publient cette période
    sur: int | None = None
    source: Source


class ProfilZone(BaseModel):
    version_socle: str
    zone: RefZone
    chiffres: list[ValeurCle]
    absents: list[RefIndicateur]  # indicateurs clés que la zone ne publie pas


class ZoneInconnue(LookupError):
    pass


def ref_zone(code: str) -> RefZone:
    z = zones().get(code)
    if z is None or z.niveau not in NIVEAUX:
        raise ZoneInconnue(code)
    return RefZone(code=z.code, libelle=z.libelle_fr, niveau=z.niveau)


def _derniere(points):
    """La dernière période publiée, jamais une projection au-delà de l'année en cours (décision 0035)."""
    passes = [p for p in points if int(p.periode[:4]) <= datetime.now(UTC).year]
    return (passes or points)[-1] if points else None


def profil(moteur, code: str) -> ProfilZone:
    zone = ref_zone(code)
    chiffres, absents, version = [], [], ""
    for cle in CHIFFRES_CLES:
        try:
            r = moteur.series(cle.code, [code])
        except IndicateurInconnu:  # absent de ce socle (faux moteur, version plus ancienne) : rien à montrer
            continue
        version = r.version_socle
        serie = r.series[0] if r.series else None
        point = _derniere(serie.points) if serie else None
        if point is None:
            absents.append(r.indicateur)
            continue
        rang = sur = None
        if zone.niveau == "region":
            classement = carte(moteur, cle.code, point.periode)
            regions = [v.region for v in classement.valeurs]  # déjà de la plus haute à la plus basse
            if code in regions and len(regions) > 1:
                rang, sur = regions.index(code) + 1, len(regions)
        chiffres.append(ValeurCle(
            theme=cle.theme, indicateur=r.indicateur, unite=r.unite, zone_servie=serie.zone,
            periode=point.periode, libelle_periode=point.libelle, valeur=point.valeur,
            valeur_affichee=point.valeur_affichee, nature=point.nature, rang=rang, sur=sur, source=serie.source,
        ))
    return ProfilZone(version_socle=version, zone=zone, chiffres=chiffres, absents=absents)
