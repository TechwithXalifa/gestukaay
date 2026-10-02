"""Référentiel des indicateurs et des domaines (issue #3, décision 0005).

Décisions :
  - un indicateur = un jeu du portail × une valeur de sa dimension « Indicateur »
    × une unité. Une dimension de mesure (« Quota », « Mesure », « Unités » :
    production / rendement / superficie, valeur / volume…) porte aussi
    l'indicateur, seule ou avec « Indicateur » : sinon des mesures différentes
    sans unité sur le portail seraient mélangées. Les autres dimensions (sexe, âge, milieu…) sont des
    désagrégations ; les dimensions géographiques donnent la zone. Un jeu sans
    dimension « Indicateur » est un seul indicateur (par unité) ;
  - l'unité fait partie de l'identité : une même série ne mélange jamais deux
    unités (comptes nationaux en prix courants ET constants, captures en
    tonnes ET en FCFA) ;
  - tout le socle entre dans le référentiel ; la colonne `verification` dit
    ce qui a été contrôlé à la main (P1 = jeu de test, P2 = domaines des
    questions types du cahier, P3 = le reste) ;
  - domaines = thèmes du portail, doublons fusionnés (`domaines.csv`).
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from .zones import normaliser

REFERENTIELS = Path(__file__).resolve().parents[2] / "referentiels"
FICHIER = REFERENTIELS / "indicateurs.csv"
FICHIER_DOMAINES = REFERENTIELS / "domaines.csv"

COLONNES = (
    "code", "dataset_id", "libelle_fr", "libelle_wo", "statut_wo", "unite", "unite_affichee", "domaine", "priorite",
    "verification", "questions_test", "producteur", "niveaux_zone", "desagregations", "frequence",
    "periode_debut", "periode_fin", "nb_valeurs", "dimension_indicateur", "valeur_portail", "jeu", "note",
)
# Colonnes remplies ou corrigées à la main : jamais écrasées par l'inventaire.
MANUELLES = ("libelle_fr", "libelle_wo", "statut_wo", "unite_affichee", "verification", "note")
VERIFICATIONS = ("a_verifier", "verifie", "ecarte")
PRIORITES = ("P1", "P2", "P3")

# indicateur, indicateurs, indicator, indicateurs-vaccination…
_DIMENSION_INDICATEUR = re.compile(r"^indicat")
# quota, mesure(s), measure(s), unités : PRODUCTION / RENDEMENT, Valeur / Volume, courants / volume
_DIMENSION_MESURE = re.compile(r"^(quota|mesures?|measures?|unites?)$")
# Valeurs d'indicateur qui ne disent rien seules : le libellé reprend le nom du jeu.
_GENERIQUES = {"total", "totaux", "ensemble", "global", "tous", "all", "valeur", "nombre"}
# « 18.3-b_ », « 11.1-11.3_ », « 22.4a_ » : numérotation des annuaires en tête des noms de jeux
_NUMERO_ANNUAIRE = re.compile(r"^\d[\d.\-a-zA-Z]*_\s*")


@dataclass(frozen=True)
class Domaine:
    theme_portail: str
    domaine: str  # vide : thème exclu (Métadonnées)
    questions_types: bool  # un des 6 domaines des questions types du cahier (priorité P2)
    note: str


@dataclass(frozen=True)
class Indicateur:
    code: str
    dataset_id: str
    libelle_fr: str
    libelle_wo: str
    statut_wo: str
    unite: str  # celle du portail : fait partie de l'identité, jamais modifiée
    unite_affichee: str  # à la main ; vide = celle du portail
    domaine: str
    priorite: str
    verification: str
    questions_test: tuple[str, ...]
    producteur: str
    niveaux_zone: tuple[str, ...]
    desagregations: tuple[str, ...]
    frequence: str
    periode_debut: str
    periode_fin: str
    nb_valeurs: int
    dimension_indicateur: str  # clé(s) dans desagregation_json (« indicateurs+mesure »), vide si aucune
    valeur_portail: str  # valeur(s) exacte(s) sur le portail, jointes par « — » ; graphies séparées par |
    jeu: str
    note: str


def est_dimension_indicateur(cle: str) -> bool:
    return bool(_DIMENSION_INDICATEUR.match(normaliser(cle)))


def dimensions_indicateur(dims: dict) -> tuple[str, ...]:
    """Clés d'une ligne du portail qui portent l'indicateur : « Indicateur » puis la mesure."""
    ind = [k for k in dims if est_dimension_indicateur(k)][:1]
    mes = [k for k in dims if _DIMENSION_MESURE.match(normaliser(k))][:1]
    return tuple(ind + mes)


def valeur_indicateur(dims: dict) -> str:
    """« Taux de pauvreté », « PRODUCTION », « Total — En milliards de francs CFA courants »."""
    return " — ".join(" ".join(str(dims[k]).split()) for k in dimensions_indicateur(dims))


def nom_du_jeu(nom: str) -> str:
    """Nom d'un jeu sans la numérotation de l'annuaire (« 12.3_Taux de chômage » -> « Taux de chômage »)."""
    return _NUMERO_ANNUAIRE.sub("", nom).strip()


def libelle(nom_jeu: str, valeur: str, mesure_seule: bool = False) -> str:
    """Libellé français initial, avant relecture. « PRODUCTION » seul ne dit rien :
    une mesure sans dimension « Indicateur » est précédée du nom du jeu."""
    if not valeur:
        return nom_du_jeu(nom_jeu)
    if mesure_seule or normaliser(valeur) in _GENERIQUES:
        return f"{nom_du_jeu(nom_jeu)} — {valeur.strip()}"
    return " ".join(valeur.split())


def _slug(texte: str, longueur: int = 48) -> str:
    s = normaliser(texte).replace(" ", "-")
    if len(s) > longueur:
        s = s[:longueur].rsplit("-", 1)[0]
    return s


def codes(identites: list[tuple[str, str, str]]) -> dict[tuple[str, str, str], str]:
    """(jeu, valeur Indicateur normalisée, unité) -> code lisible : « dwibrlf »,
    « jcvcajc.taux-de-pauvrete ». En cas de doublon :
      1. libellés longs tronqués au même endroit : libellé plus long, puis
         suffixe tiré du libellé ;
      2. même indicateur en plusieurs unités : la partie de l'unité qui les
         distingue (« uipcgjd.total~courants » / « ~aux-prix-constants-de-1999 ») ;
      3. dernier recours : suffixe tiré de l'identité complète.
    Le code est stable tant que le socle ne change pas ; sinon l'inventaire
    signale les codes disparus."""
    def regrouper(d: dict) -> list[list]:
        g: dict[str, list] = {}
        for i, c in d.items():
            g.setdefault(c, []).append(i)
        return list(g.values())

    base = {i: (f"{i[0]}.{_slug(i[1])}" if _slug(i[1]) else i[0]) for i in identites}
    for membres in regrouper(base):
        if len({i[1] for i in membres}) > 1:
            for i in membres:
                base[i] = f"{i[0]}.{_slug(i[1], 96)}"
    for membres in regrouper(base):
        if len({i[1] for i in membres}) > 1:
            for i in membres:
                base[i] += "-" + hashlib.sha1(i[1].encode()).hexdigest()[:4]

    out = {}
    for membres in regrouper(base):
        if len(membres) == 1:
            out[membres[0]] = base[membres[0]]
            continue
        mots = {i: _slug(i[2], 200).split("-") if i[2] else [] for i in membres}
        commun = 0  # mots communs en tête de toutes les unités du groupe
        while all(len(m) > commun for m in mots.values()) and len({m[commun] for m in mots.values()}) == 1:
            commun += 1
        for i in membres:
            reste = "-".join(mots[i][commun:]) or _slug(i[2], 200) or "sans-unite"
            out[i] = f"{base[i]}~{_slug(reste, 32)}"

    vus: dict[str, int] = {}
    for c in out.values():
        vus[c] = vus.get(c, 0) + 1
    return {i: (f"{c}-{hashlib.sha1('|'.join(i).encode()).hexdigest()[:4]}" if vus[c] > 1 else c)
            for i, c in out.items()}


@cache
def domaines() -> dict[str, Domaine]:
    """Thème du portail -> domaine Gëstukaay."""
    with FICHIER_DOMAINES.open(encoding="utf-8") as f:
        return {
            r["theme_portail"]: Domaine(r["theme_portail"], r["domaine"], r["questions_types"] == "oui", r["note"])
            for r in csv.DictReader(f, delimiter=";")
        }


def _liste(v: str) -> tuple[str, ...]:
    return tuple(x for x in v.split("|") if x)


@cache
def indicateurs() -> dict[str, Indicateur]:
    with FICHIER.open(encoding="utf-8") as f:
        return {
            r["code"]: Indicateur(**{
                **r,
                "questions_test": _liste(r["questions_test"]),
                "niveaux_zone": _liste(r["niveaux_zone"]),
                "desagregations": _liste(r["desagregations"]),
                "nb_valeurs": int(r["nb_valeurs"]),
            })
            for r in csv.DictReader(f, delimiter=";")
        }
