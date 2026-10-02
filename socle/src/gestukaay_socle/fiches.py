"""Fiches des jeux du portail : définition, méthode, opération (issue #7).

La fiche d'un indicateur (cahier 10.3, US « consulter la définition ») réunit :
  - le référentiel des indicateurs : libellés FR/WO, unité, périmètre, et une
    définition propre à l'indicateur quand le jeu en décrit plusieurs ;
  - la fiche de son jeu (`jeux.csv`) : définition, type de données, opération,
    méthode de calcul, observations, découpées dans la description du portail.

Rien n'est rédigé ici : on découpe ce que publie le portail. Les annuaires ANSD
suivent un modèle en 6 rubriques (« 1. Intitulé de l'indicateur … 6. Observations
sur la série ») ; les autres descriptions sont gardées en texte libre.
"""

from __future__ import annotations

import csv
import html
import re
from dataclasses import dataclass
from functools import cache

from .indicateurs import REFERENTIELS

FICHIER_JEUX = REFERENTIELS / "jeux.csv"
COLONNES_JEUX = ("dataset_id", "intitule", "definition", "type_donnees", "operation", "methode",
                 "observations", "description")

# Rubriques du modèle des annuaires, dans l'ordre
_RUBRIQUES = (
    ("intitule", r"Intitul[ée] de l['’]indicateur"),
    ("definition", r"D[ée]finition de l['’]indicateur"),
    ("type_donnees", r"Type de donn[ée]es"),
    ("operation", r"Op[ée]ration"),
    ("methode", r"M[ée]thode de calcul"),
    ("observations", r"Observations sur la s[ée]rie"),
)
_VIDES = {"NEANT", "NÉANT", "NA", "-", "RAS"}
_TITRE = re.compile(r"(?<![\d,.])\d\s?\.\s?(?:" + "|".join(f"(?P<{k}>{m})" for k, m in _RUBRIQUES) + ")")


@dataclass(frozen=True)
class FicheJeu:
    dataset_id: str
    intitule: str
    definition: str
    type_donnees: str
    operation: str  # RGPH-5, EHCVM, ENES… : Source.operation du contrat
    methode: str
    observations: str
    description: str  # texte libre, quand le jeu ne suit pas le modèle des annuaires


def nettoyer(texte: str) -> str:
    """Texte du portail -> une ligne lisible (balises, entités, espaces insécables)."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", texte or ""))
    return re.sub(r"\s+", " ", t.replace("\xa0", " ")).strip()


def decouper(texte: str) -> dict[str, str]:
    """Description du portail -> rubriques. Sans le modèle des annuaires : tout dans « description »."""
    t = nettoyer(texte)
    titres = list(_TITRE.finditer(t))
    vus = {m.lastgroup for m in titres}
    if not {"definition", "operation"} <= vus:
        return {"description": t}
    out = {}
    for m, suivant in zip(titres, [*titres[1:], None], strict=True):
        fin = suivant.start() if suivant else len(t)
        valeur = t[m.end():fin].strip(" :.-")
        out.setdefault(m.lastgroup, "" if valeur.upper() in _VIDES else valeur)
    return out


@cache
def jeux() -> dict[str, FicheJeu]:
    with FICHIER_JEUX.open(encoding="utf-8") as f:
        return {r["dataset_id"]: FicheJeu(**r) for r in csv.DictReader(f, delimiter=";")}
