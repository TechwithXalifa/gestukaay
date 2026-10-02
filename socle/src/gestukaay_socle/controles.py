"""Contrôles du socle et corrections déclarées (issue #6, décision 0008).

Deux mécanismes distincts :
  - les CONTRÔLES signalent (rapport), ils n'excluent rien : une vraie rupture
    (crise, changement de base) ne doit pas disparaître automatiquement ;
  - les CORRECTIONS (`corrections.csv`) sont décidées à la main, une par ligne,
    avec leur motif et leur preuve. Seules deux actions existent :
      * exclure : la valeur part dans les rejets (motif « correction Cxx ») ;
      * unite_affichee : l'unité montrée au public (métadonnée, jamais le nombre).
    On ne répare jamais une valeur (pas de réattribution à une autre zone).
"""

from __future__ import annotations

import csv
import fnmatch
import itertools
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .indicateurs import REFERENTIELS, Indicateur

FICHIER_CORRECTIONS = REFERENTIELS / "corrections.csv"
ACTIONS = ("exclure", "unite_affichee")
CONDITIONS = ("", "valeur=0", "journalier")

# Indices des colonnes d'une observation (voir extraction.COLONNES_OBSERVATIONS)
_IND, _ZONE, _PER, _DESAG, _VAL, _UNITE, _SRC, _LIGNE = 1, 2, 4, 5, 6, 7, 9, 12


@dataclass(frozen=True)
class Correction:
    id: str
    action: str
    dataset_id: str
    indicateur: str  # code, motif (« qjyrtof.* ») ou « unite:<motif> » sur l'unité du portail ; vide = tout le jeu
    zones: tuple[str, ...]  # vide = toutes
    periode_debut: str
    periode_fin: str
    condition: str
    valeur: str  # unite_affichee : la nouvelle unité
    motif: str
    preuve: str

    def cible(self, code: str, unite: str) -> bool:
        """L'indicateur (code, unité du portail) est-il visé ?"""
        if not self.indicateur:
            return True
        if self.indicateur.startswith("unite:"):
            return fnmatch.fnmatchcase(unite, self.indicateur[len("unite:"):])
        return fnmatch.fnmatchcase(code, self.indicateur)

    def vise(self, o: tuple) -> bool:
        """Cette correction s'applique-t-elle à l'observation o ?"""
        annee = o[_PER][:4]
        return (o[_SRC] == self.dataset_id
                and self.cible(o[_IND], o[_UNITE])
                and (not self.zones or o[_ZONE] in self.zones)
                and (not self.periode_debut or annee >= self.periode_debut)
                and (not self.periode_fin or annee <= self.periode_fin)
                and (self.condition != "valeur=0" or float(o[_VAL]) == 0)
                and (self.condition != "journalier" or len(o[_PER]) == 10))


def corrections() -> list[Correction]:
    with FICHIER_CORRECTIONS.open(encoding="utf-8") as f:
        return [Correction(**{**r, "zones": tuple(z for z in r["zones"].split("|") if z)})
                for r in csv.DictReader(f, delimiter=";")]


def appliquer(observations: list[tuple], corr: list[Correction]) -> tuple[list[tuple], list[tuple], Counter]:
    """Exclusions déclarées -> (observations gardées, rejets, nombre d'exclusions par correction)."""
    exclusions = [c for c in corr if c.action == "exclure"]
    gardees, rejets, compte = [], [], Counter()
    for o in observations:
        c = next((c for c in exclusions if c.vise(o)), None)
        if c is None:
            gardees.append(o)
        else:
            compte[c.id] += 1
            rejets.append((o[_LIGNE], o[_SRC], o[_IND], f"correction {c.id}", c.motif))
    return gardees, rejets, compte


# --------------------------------------------------------------------------
# Contrôles automatiques : ils signalent, ils n'excluent pas
# --------------------------------------------------------------------------

def _est_pourcentage(ind: Indicateur | None) -> bool:
    return bool(ind) and "%" in (ind.unite_affichee or ind.unite)


def controler(observations: list[tuple], indicateurs: dict[str, Indicateur]) -> dict[str, list[str]]:
    """Signalements par contrôle (une ligne lisible par anomalie)."""
    s: dict[str, list[str]] = defaultdict(list)
    series: dict[tuple, list[tuple[str, float]]] = defaultdict(list)
    for o in observations:
        ind = indicateurs.get(o[_IND])
        v = float(o[_VAL])
        annee = o[_PER][:4]
        cle = f"`{o[_IND]}` {o[_ZONE]} {o[_PER]} {o[_DESAG]} = {o[_VAL]}"
        if _est_pourcentage(ind) and not 0 <= v <= 100:
            s["pourcentage hors de 0-100"].append(cle)
        if "gini" in o[_IND] and not 0 < v < 1:
            s["Gini hors de ]0, 1["].append(cle)
        if not "1900" <= annee <= "2100":
            s["date impossible"].append(cle)
        if len(o[_PER]) == 4:
            series[(o[_IND], o[_ZONE], o[_DESAG])].append((o[_PER], v))
    for (code, zone, desag), points in series.items():
        points.sort()
        for (p1, v1), (p2, v2) in itertools.pairwise(points):
            if int(p2) - int(p1) == 1 and v1 > 0 and v2 > 0 and not 1 / 3 <= v2 / v1 <= 3 \
                    and not _est_pourcentage(indicateurs.get(code)):
                s["rupture (×3 d'une année sur l'autre)"].append(f"`{code}` {zone} {desag} : {p1} = {v1:g} → {p2} = {v2:g}")
    return dict(s)


def controle_population(observations: list[tuple]) -> list[str]:
    """Population régionale de rnumqzf (dernière année avant 2023) comparée au RGPH-5 2023 (pvswjnd) :
    un écart de plus de 15 % trahit une permutation de lignes."""
    rgph, estim = {}, {}
    for o in observations:
        d = json.loads(o[_DESAG])
        if o[_IND] == "pvswjnd" and d.get("sexe") == "Total" and d.get("age") == "Total":
            rgph[o[_ZONE]] = float(o[_VAL])
        elif (o[_IND].startswith("rnumqzf") and o[_PER] == "2022"
              and d == {"groupe-d-âge": "Ensemble", "sexe": "TOTALE"}):
            estim[o[_ZONE]] = float(o[_VAL])
    return [f"{z} : rnumqzf 2022 = {estim[z]:,.0f} ; RGPH-5 2023 = {rgph[z]:,.0f}".replace(",", " ")
            for z in sorted(rgph) if z in estim and not 0.85 <= estim[z] / rgph[z] <= 1.15]


def unites_incrementees(indicateurs: dict[str, Indicateur]) -> dict[str, int]:
    """Jeux dont l'unité « prix constants de AAAA » change d'année d'un indicateur à l'autre."""
    annees: dict[str, set] = defaultdict(set)
    for x in indicateurs.values():
        if m := re.search(r"prix constants de (\d{4})", x.unite):
            annees[x.dataset_id].add(m.group(1))
    return {ds: len(a) for ds, a in annees.items() if len(a) > 1}
