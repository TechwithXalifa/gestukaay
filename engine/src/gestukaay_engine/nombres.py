"""Nombres dits en lettres -> chiffres, après la transcription d'une note vocale (#28, décision 0027).

La transcription écrit souvent les nombres comme ils sont dits : « en deux mille vingt quatre »,
« de quinze à vingt-quatre ans ». Le moteur attend des chiffres (« 2024 », « 15 à 24 ») pour
reconnaître une année ou une tranche d'âge. Seuls les nombres français sont convertis pour
l'instant ; les nombres wolof viendront avec les mots écrits par KBD (0009).

Prudence : un « un » ou « une » isolé est un article (« un kilo »), jamais converti ; rien d'autre
que les suites de mots-nombres n'est touché.
"""

from __future__ import annotations

import re
import unicodedata

_UNITES = {
    "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7,
    "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14,
    "quinze": 15, "seize": 16, "vingt": 20, "vingts": 20, "trente": 30, "quarante": 40,
    "cinquante": 50, "soixante": 60,
}
_MULTIPLES = {"cent": 100, "cents": 100, "mille": 1000, "million": 10**6, "millions": 10**6,
              "milliard": 10**9, "milliards": 10**9}
_MOTS = set(_UNITES) | set(_MULTIPLES)


def _sans_accent(mot: str) -> str:
    return unicodedata.normalize("NFKD", mot.lower()).encode("ascii", "ignore").decode()


def _valeur(mots: list[str]) -> int:
    """Valeur d'une suite de mots-nombres français (sans « et »)."""
    total, courant, precedent = 0, 0, None
    for m in mots:
        if m in ("vingt", "vingts") and precedent == "quatre":  # quatre-vingt(s) = 80
            courant += 80 - 4
        elif m in ("cent", "cents"):
            courant = (courant or 1) * 100
        elif m in _MULTIPLES:  # mille, million, milliard
            total += (courant or 1) * _MULTIPLES[m]
            courant = 0
        else:
            courant += _UNITES[m]
        precedent = m
    return total + courant


def _jetons(texte: str) -> list[str]:
    """Mots et séparateurs gardés : on réécrit le texte à l'identique hors des nombres."""
    return re.findall(r"[A-Za-zÀ-ÿ]+|\s+|[^\sA-Za-zÀ-ÿ]", texte)


def en_chiffres(texte: str) -> str:
    """« en deux mille vingt-quatre » -> « en 2024 » ; « treize virgule deux » -> « 13,2 »."""
    jetons = _jetons(texte)
    sortie: list[str] = []
    i = 0
    while i < len(jetons):
        run, j = _suite(jetons, i)
        isole = len(run) == 1 and (run[0] in ("un", "une") or (run[0] == "cent" and _avant(sortie) == "pour"))
        if run and not isole:  # « un kilo », « pour cent » : pas des nombres
            nombre = str(_valeur(run))
            # décimales : « treize virgule deux »
            k = j
            while k < len(jetons) and jetons[k].isspace():
                k += 1
            if k < len(jetons) and _sans_accent(jetons[k]) == "virgule":
                k += 1
                while k < len(jetons) and jetons[k].isspace():
                    k += 1
                apres, fin = _suite(jetons, k)
                if apres:
                    nombre, j = f"{nombre},{_valeur(apres)}", fin
            sortie.append(nombre)
            i = j
            continue
        sortie.append(jetons[i])
        i += 1
    return "".join(sortie)


def _avant(sortie: list[str]) -> str:
    """Dernier mot déjà écrit (sans accent), pour « pour cent »."""
    return next((_sans_accent(t) for t in reversed(sortie) if not t.isspace()), "")


def _suite(jetons: list[str], i: int) -> tuple[list[str], int]:
    """Plus longue suite de mots-nombres à partir de jetons[i] (espaces, tirets et « et » internes
    admis) : (mots, index de fin). Vide si jetons[i] n'est pas un mot-nombre."""
    if i >= len(jetons) or jetons[i].isspace():
        return [], i
    mots: list[str] = []
    fin = i
    k = i
    while k < len(jetons):
        t = jetons[k]
        m = _sans_accent(t)
        if m in _MOTS:
            mots.append(m)
            fin = k + 1
        elif t.isspace() or t == "-" or (m == "et" and mots):
            pass  # liaison possible ; validée seulement si un mot-nombre suit
        else:
            break
        k += 1
    return mots, fin
