"""Référentiel des zones et rattachement des libellés géographiques.

Décisions (issue #2) :
  - niveaux : pays, 14 régions (codes ISO 3166-2), 46 départements ;
  - départements : codes lisibles Gëstukaay SN-<région>-<NOM>. Les codes
    départementaux du portail sont incohérents (Vélingara rangé sous Matam)
    et 331 000 valeurs n'ont aucun code : les libellés sont rattachés par
    leur NOM ;
  - homonymes (« Kaolack » = région ET département) : la RÉGION par défaut.
    Le département n'est retenu que si le contexte l'indique : préfixe
    « Dpt » / « Département », ou niveau="departement" passé par l'appelant
    (colonne « département » d'un jeu) ;
  - « Total », « ALL », « Ensemble » ne sont jamais rattachés : ils sont
    traités jeu par jeu à l'extraction (#4) ;
  - académies (inspections d'académie, données d'éducation) : niveau à part,
    jamais choisi par défaut. Reconnues seulement si le contexte le dit
    (colonne « académie », préfixe « IA »). La colonne `couvre` donne les
    zones administratives qu'elles recouvrent : IA Pikine-Guédiawaye couvre
    trois départements, elle n'est égale à aucun.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from functools import cache
from pathlib import Path

FICHIER = Path(__file__).resolve().parents[2] / "referentiels" / "zones.csv"

# Ordre de choix quand le contexte n'impose pas de niveau (règle des homonymes).
# « academie » n'y figure pas : jamais choisi par défaut.
NIVEAUX = ("pays", "region", "departement")


@dataclass(frozen=True)
class Zone:
    code: str
    niveau: str  # pays | region | departement | academie
    parent: str | None
    libelle_fr: str
    libelle_wo: str
    statut_wo: str
    variantes: tuple[str, ...]
    couvre: tuple[str, ...]  # académies : zones administratives recouvertes


def normaliser(texte: str) -> str:
    """Minuscules, sans accents, sans apostrophes (M'bour = Mbour) ;
    tirets et ponctuation -> espace (Saint-Louis = Saint Louis)."""
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    t = re.sub(r"['`]", "", t.lower())
    t = re.sub(r"[\-_/().,]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@cache
def zones() -> dict[str, Zone]:
    with FICHIER.open(encoding="utf-8") as f:
        return {
            r["code"]: Zone(
                code=r["code"],
                niveau=r["niveau"],
                parent=r["parent"] or None,
                libelle_fr=r["libelle_fr"],
                libelle_wo=r["libelle_wo"],
                statut_wo=r["statut_wo"],
                variantes=tuple(v for v in r["variantes"].split("|") if v),
                couvre=tuple(c for c in r["couvre"].split("|") if c),
            )
            for r in csv.DictReader(f, delimiter=";")
        }


@cache
def _index() -> dict[str, dict[str, str]]:
    """Nom normalisé -> {niveau: code}. Un nom peut exister à deux niveaux."""
    idx: dict[str, dict[str, str]] = {}
    for z in zones().values():
        for nom in (z.libelle_fr, z.libelle_wo, *z.variantes):
            idx.setdefault(normaliser(nom), {}).setdefault(z.niveau, z.code)
    return idx


# Préfixes / suffixes qui fixent le niveau. L'ordre compte : le plus long d'abord.
_MARQUEURS = [
    (re.compile(r"^(ia|inspection academique|academie) (de |du |d )?"), "academie"),
    (re.compile(r"^(departement|department|dpt|dept) (de |du |d )?"), "departement"),
    (re.compile(r" (departement|department)$"), "departement"),
    (re.compile(r"^(region|regions) (de |du |d )?"), "region"),
    (re.compile(r" region$"), "region"),
]

_JAMAIS = {"total", "totaux", "all", "ensemble", "ensemble national"}


def niveau_de_colonne(cle: str) -> str | None:
    """Niveau imposé par le nom d'une colonne d'un jeu du portail, s'il y en a un."""
    c = normaliser(cle)
    if "academ" in c:
        return "academie"
    if "depart" in c and "region" not in c:
        return "departement"
    return None


@cache
def resoudre(libelle: str, niveau: str | None = None) -> str | None:
    """Libellé libre -> code de zone, ou None s'il n'est pas rattachable.

    niveau : « region », « departement » ou « academie » quand la colonne du
    jeu l'impose (voir niveau_de_colonne).
    Un marqueur dans le libellé (« Dpt », « Région de ») l'emporte sur niveau.
    """
    nom = normaliser(libelle)
    if not nom or nom in _JAMAIS:
        return None
    for motif, niv in _MARQUEURS:
        if motif.search(nom):
            nom, niveau = motif.sub("", nom).strip(), niv
            break

    par_niveau = _index().get(nom)
    if not par_niveau:
        return None
    if niveau in par_niveau:
        return par_niveau[niveau]
    for defaut in NIVEAUX:  # région avant département : règle des homonymes
        if defaut in par_niveau:
            return par_niveau[defaut]
    return None
