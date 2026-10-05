"""Indicateur compagnon : un nombre accompagné de son taux (décision 0024).

« Ñi amul ligéey ci Senegaal ? » demande combien de personnes sont sans emploi ; la réponse donne le
nombre, puis le taux de chômage pour le rendre parlant. Les paires sont déclarées à la main et
vérifiées (`socle/referentiels/indicateurs_compagnons.csv`) : rien n'est deviné.

Le compagnon n'est servi que s'il est publié pour la MÊME zone, la MÊME période et les mêmes
modalités que la valeur demandée : on ne mélange jamais deux périodes, et rien n'est calculé.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import cache

from gestukaay_contracts.models import Resultat
from gestukaay_socle.indicateurs import REFERENTIELS, indicateurs

from .gabarits import formater
from .resolution import resultat
from .socle import Socle

FICHIER = REFERENTIELS / "indicateurs_compagnons.csv"


@dataclass(frozen=True)
class Compagnon:
    code: str
    phrase: str  # trous : {nombre} (valeur du compagnon, mise en forme), {valeur} (avec son unité)


@cache
def compagnons() -> dict[str, Compagnon]:
    with FICHIER.open(encoding="utf-8") as f:
        return {r["code"]: Compagnon(r["compagnon"], r["phrase"]) for r in csv.DictReader(f, delimiter=";")}


def compagnon(socle: Socle, r: Resultat, langue: str = "fr") -> tuple[Resultat, str] | None:
    """(résultat du compagnon, phrase) si le compagnon est publié au même point ; sinon None."""
    c = compagnons().get(r.indicateur.code)
    if c is None:
        return None
    o = next((x for x in socle.observations(r.indicateur.code) if x.id == r.observation_id), None)
    lignes = socle.observations(c.code)
    meme = next((x for x in lignes if o is not None and x.zone == o.zone and x.periode == o.periode
                 and x.desagregation == o.desagregation), None)
    if meme is None:
        return None
    uniques = frozenset(k for k in {k for x in lignes for k, _ in x.desagregation}
                        if len({x.dims().get(k) for x in lignes} - {None}) == 1)
    rc = resultat(socle, meme, indicateurs()[c.code], langue, uniques)
    nombre = formater(rc.valeur, rc.unite)[0]
    return rc, c.phrase.format(nombre=nombre, valeur=rc.valeur_affichee)
