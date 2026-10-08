"""Messages qui ne sont pas des questions de statistique (décision 0033, contrat 1.5.0).

Le LLM (dans le même appel que la compréhension) ou, à défaut, les règles ci-dessous rangent le message
dans une catégorie ; chaque catégorie a une réponse FIXE, écrite par KBD en wolof (0009), jamais générée.
Une case wolof vide fait partir le français (choix de KBD, 0032). La définition vient du socle
(colonne `definition` de indicateurs.csv) ; « pourquoi » et « définition » proposent le chiffre lié.

Les règles sont prudentes : elles ne reconnaissent que les formes sûres (salutations de KBD, « merci »,
« qui es-tu », « c'est quoi… », quelques hors-sujet évidents : météo, président, poème…). Le reste du hors
sujet et l'impolitesse ne viennent que du LLM.
"""

from __future__ import annotations

import csv
import re
from functools import cache
from pathlib import Path
from typing import Literal

from gestukaay_socle.zones import normaliser

from .candidats import SYNONYMES, mots, periodes_citees, zones_citees

ICI = Path(__file__).resolve().parent

Categorie = Literal["salutation", "remerciement", "au_revoir", "a_propos", "langue", "aide", "definition",
                    "pourquoi", "hors_sujet", "impoli"]
CATEGORIES: tuple[str, ...] = Categorie.__args__


@cache
def _textes() -> dict[str, tuple[str, str]]:
    with (ICI / "conversation.csv").open(encoding="utf-8") as f:
        return {r["cle"]: (r["fr"], r["wo"]) for r in csv.DictReader(f, delimiter=";")}


def texte(cle: str, langue: str = "fr", **trous: str) -> str:
    fr, wo = _textes()[cle]
    t = (wo if langue == "wo" and wo.strip() else fr).format(**trous).strip()
    # à l'écrit, le sigle tel qu'écrit (0032) ; le texte de KBD garde la forme parlée pour la voix
    return t.replace("A-EN-ES-DE", "ANSD")


def _t(question: str) -> str:
    t = question.replace("ŋ", "ng").replace("Ŋ", "Ng")
    return " " + normaliser(re.sub(r"['’`?!;:\"]", " ", t)) + " "


# Formes sûres seulement (sans accents). Salutations : formes de KBD, écritures francisées comprises
# (« ou » / « u », « dj » / « j », lettres doublées), sur les seuls mots wolof.
_REGLES: tuple[tuple[str, re.Pattern], ...] = (
    ("salutation", re.compile(
        r"^ (bonjour|bonsoir|salut|hello|coucou|salam\w*|asalaa?m\w*|as+alamo?u? ale?ykou?m|naka( \w+){0,2}|"
        r"na ?nga def|na ?ngee?n def|lo?u be+s+|d?ja+m+ nga am|ya ?ngi ci d?ja+m+|comment (tu vas|allez vous|ca va)|"
        r"ca va)( \w+){0,2} $")),
    ("remerciement", re.compile(r"^ (merci( beaucoup| bien)?|jerejef|jerrejef|jerejeuf) ")),
    ("au_revoir", re.compile(r"^ (au revoir|a plus|a bientot|bye|ciao|ba beneen yoon) ")),
    ("a_propos", re.compile(r" (qui es tu|tu es qui|t es qui|qui t a (cree|fait|developpe)|tu es un robot|"
                            r"c est quoi gestukaay|qu est ce que gestukaay|d ou viennent tes (chiffres|donnees)) ")),
    ("langue", re.compile(r" (tu parles? (le )?wolof|repondre en wolof|reponds en wolof|parles tu wolof|"
                          r"quelles? langues?) ")),
    ("aide", re.compile(r"^ (aide moi|je peux (te )?demander quoi|que (sais|peux) tu faire|tu fais quoi|"
                        r"que puis je (te )?demander) ")),
    # « Lou gestukay meune def », « … lane leu gestukaay meune def » : formes de KBD (essai Telegram, 08/10)
    ("aide", re.compile(r" (lu|lou|lan|lane) (la |leu |le )?ge?stu?kaa?y (meune?|mene?|mun) def ")),
    ("definition", re.compile(r"^ (c est quoi|qu est ce que?|que veut dire|ca veut dire quoi|definition( de| du)?|"
                              r"definis?) ")),
    ("pourquoi", re.compile(r"^ (pourquoi|que pensez vous|qu en penses tu|tu penses que) ")),
    # hors sujet SÛR seulement (le reste : LLM) ; « njiitu réew » : question WO-025 de KBD
    # pas « recette », « foot », « match », « président » seuls : « recette touristique », « terrains de foot »
    # sont des questions de statistique (revue de SAN sur #147)
    # questions de KBD du 08/10 : une personne (maire, vainqueur), une capitale, les points cardinaux
    ("hors_sujet", re.compile(r" (meteo|temps fera t il|quel temps fera|qui est le president|njiitu reew\w*|"
                              r"poeme|blague|qui est le maire|qui a (remporte|gagne)|capitale (de|du|des)|"
                              r"points? cardinaux|"
                              # mêmes questions en wolof (KBD, 08/10) : maire, vainqueur, capitale, points cardinaux
                              r"meeru|kan moo jel|peyum|jubluwaay\w*|campiyong\w*) ")),
)


def naka_sujet(question: str) -> bool:
    """« Naka njëg ceeb », « Naka mbëj bi », « Naka Kaolack ? » : « naka » (comment) suivi d'un sujet
    statistique ou d'un lieu est une question, pas une salutation (revue de SAN sur #137 et #140).
    La règle de KBD « naka + un mot = salutation » vaut pour les autres mots (« naka leu », « nakamu »)."""
    return bool(zones_citees(question) or periodes_citees(question)
                or any(m in SYNONYMES for m in mots(question) if m != "naka"))


def regles(question: str) -> str | None:
    """Catégorie de conversation par les formes sûres, ou None (question de statistique, ou autre)."""
    t = _t(question)
    cle = next((cle for cle, motif in _REGLES if motif.search(t)), None)
    if cle == "salutation" and t.split()[0] == "naka" and naka_sujet(question):
        return None
    return cle


# Formules de politesse FIXES qui peuvent précéder une question : « Bonjour, combien d'habitants à
# Thiès ? », « Merci. Et à Dakar ? ». Retirées avant la compréhension, quoi que dise le LLM (revue de SAN :
# le LLM gardait parfois la politesse seule). Pas « naka + mot » : « Naka njëg ceeb » est une question.
_POLITESSE = re.compile(
    r"^ ((bonjour|bonsoir|salut|hello|coucou|salam|salamaleekum|aleykoum|alekum|asalaa?maa?le?kum|"
    r"as+alamo?u?|ale?ykou?m|merci|beaucoup|jerejef|jerrejef|naka nga def|na ?nga def|na ?ngee?n def|"
    r"comment (tu vas|allez vous|ca va)|ca va|madame|monsieur) ?)+ $")


def sans_politesse(question: str) -> str:
    """La question sans la politesse de tête ; inchangée s'il n'y a pas de politesse ou rien après."""
    # tout le message est une formule (« Merci beaucoup », « Salam naka leu ») : on n'y touche pas
    if _POLITESSE.match(_t(question)) or regles(question) == "salutation":
        return question
    jetons = question.split()
    for k in range(min(len(jetons) - 1, 6), 0, -1):  # le plus long préfixe de politesse d'abord
        if _POLITESSE.match(_t(" ".join(jetons[:k]))):
            reste = " ".join(jetons[k:]).lstrip(" ,.;:!-–")
            # rien après, ou encore une salutation (« Salam naka leu ») : tout le message est la salutation
            return reste if len(reste) >= 3 and regles(reste) is None else question
    return question
