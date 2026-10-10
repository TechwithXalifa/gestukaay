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

from gestukaay_engine.conversation import naka_sujet

ICI = Path(__file__).resolve().parent


@cache
def _textes() -> dict[str, tuple[str, str]]:
    with (ICI / "textes.csv").open(encoding="utf-8") as f:
        return {r["cle"]: (r["fr"].replace("\\n", "\n"), r["wo"].replace("\\n", "\n"))
                for r in csv.DictReader(f, delimiter=";")}


def texte(cle: str, langue: str | None = None) -> str:
    """Le texte fixe, wolof puis français (l'accueil, déjà bilingue, n'a qu'une colonne). Langue connue (« fr »,
    « wo ») : cette langue seule (#274 : une réponse française finissait par la consigne en wolof) ; une case
    wolof vide donne le français."""
    fr, wo = _textes()[cle]
    if langue == "fr" and fr:
        return fr
    if langue == "wo" and wo:
        return wo
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


# ---------------------------------------------------------------------------
# Salutations (formes de KBD, 07/10) : un message qui n'est QUE salutation reçoit l'accueil ; suivie
# d'une question (« Salam, ñaata nit ñoo dëkk Tiés ? »), la salutation laisse partir la question.
# ---------------------------------------------------------------------------


def plier(texte_: str) -> str:
    """Comme `mot`, en ignorant les écritures francisées (conseil de KBD) : « ou » = « u », « dj » = « j »,
    lettres doublées simples (« jàmm » = « djam », « bees » = « bess » -> « bes »)."""
    return re.sub(r"(\w)\1+", r"\1", mot(texte_).replace("ou", "u").replace("dj", "j"))


@cache
def _salutations() -> tuple[str, ...]:
    with (ICI / "salutations.csv").open(encoding="utf-8") as f:
        formes = {plier(x) for r in csv.DictReader(f, delimiter=";") for x in r["formes"].split("|") if x.strip()}
    return tuple(sorted(formes, key=len, reverse=True))  # la plus longue d'abord : « salam aleykoum » avant « salam »


def est_salutation(message: str) -> bool:
    """« /start » (Telegram), « Salam naka leu », « Naka nga def ? », « Bonjour » ; pas « Salam, ñaata… »."""
    if message.strip().lower().startswith("/start"):
        return True
    reste = plier(message)
    if not reste or len(reste.split()) > 8:
        return False
    if reste.split()[0] == "naka" and len(reste.split()) <= 3:  # KBD : « naka » + un mot = salutation,
        return not naka_sujet(message)  # sauf « Naka njëg ceeb », « Naka Kaolack ? » : des questions (SAN)
    while reste:
        forme = next((f for f in _salutations() if reste == f or reste.startswith(f + " ")), None)
        if forme is None:
            return False
        reste = reste[len(forme):].strip()
    return True

