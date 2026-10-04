"""Textes fixes du canal et mots de commande (décision 0025).

Le wolof est écrit par KBD (décision 0009) dans `textes.csv` et `commandes.csv` ; rien n'est généré.
Tant que la détection de la langue (#24) manque, un texte fixe part en wolof puis en français ; une
case wolof vide fait partir le français seul (jamais de texte provisoire visible).

Une commande n'est reconnue que si le message ne contient qu'elle (« taxaw », « 2 », « Ñaar ! ») :
dans une phrase, « bayyi » ou « un » ne sont pas des commandes.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from functools import cache
from pathlib import Path

ICI = Path(__file__).resolve().parent


@cache
def _textes() -> dict[str, tuple[str, str]]:
    with (ICI / "textes.csv").open(encoding="utf-8") as f:
        return {r["cle"]: (r["fr"].replace("\\n", "\n"), r["wo"].replace("\\n", "\n"))
                for r in csv.DictReader(f, delimiter=";")}


def texte(cle: str) -> str:
    """Le texte fixe, wolof puis français (l'accueil, déjà bilingue, n'a qu'une colonne)."""
    fr, wo = _textes()[cle]
    return "\n".join(x for x in (wo, fr) if x)


def bouton_liste() -> str:
    """Libellé du bouton d'une liste WhatsApp : 20 caractères au plus."""
    fr, wo = _textes()["bouton_liste"]
    libelle = " / ".join(x for x in (wo, fr) if x)
    return libelle if len(libelle) <= 20 else (wo or fr)[:20]


def mot(texte_: str) -> str:
    """Forme comparable d'un message court : minuscules, sans accents (ñ -> n), sans ponctuation
    autour (« Ñaar ! » -> « naar »), le « ? » seul étant gardé (aide)."""
    t = unicodedata.normalize("NFKD", texte_.strip().lower()).encode("ascii", "ignore").decode()
    if t.strip() == "?":
        return "?"
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


@cache
def _commandes() -> dict[str, str]:
    with (ICI / "commandes.csv").open(encoding="utf-8") as f:
        return {mot(m): r["commande"] for r in csv.DictReader(f, delimiter=";") for m in r["mots"].split("|")}


def commande(message: str) -> str | None:
    """« aide », « exemples », « langue », « stop », « 1 », « 2 », « 3 », ou None."""
    return _commandes().get(mot(message)) if len(message) <= 30 else None
