"""Messages qui ne sont pas des questions de statistique (décision 0033, contrat 1.5.0).

Le LLM (dans le même appel que la compréhension) ou, à défaut, les règles ci-dessous rangent le message
dans une catégorie ; chaque catégorie a une réponse FIXE, écrite par KBD en wolof (0009), jamais générée.
Une case wolof vide fait partir le français (choix de KBD, 0032). La définition vient du socle
(colonne `definition` de indicateurs.csv) ; « pourquoi » et « définition » proposent le chiffre lié.

Les règles sont prudentes : elles ne reconnaissent que les formes sûres (salutations de KBD, « merci »,
« qui es-tu », « c'est quoi… »). Le hors sujet et l'impolitesse ne viennent que du LLM : sans lui, ces
messages restent des refus « hors_socle », comme avant.
"""

from __future__ import annotations

import csv
import re
from functools import cache
from pathlib import Path
from typing import Literal

from gestukaay_socle.zones import normaliser

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
    ("definition", re.compile(r"^ (c est quoi|qu est ce que?|que veut dire|ca veut dire quoi|definition( de| du)?|"
                              r"definis?) ")),
    ("pourquoi", re.compile(r"^ (pourquoi|que pensez vous|qu en penses tu|tu penses que) ")),
)


def regles(question: str) -> str | None:
    """Catégorie de conversation par les formes sûres, ou None (question de statistique, ou autre)."""
    t = _t(question)
    return next((cle for cle, motif in _REGLES if motif.search(t)), None)
