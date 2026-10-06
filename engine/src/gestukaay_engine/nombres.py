"""Nombres dits en lettres -> chiffres, après la transcription d'une note vocale (#28, décision 0027).

La transcription écrit souvent les nombres comme ils sont dits : « en deux mille vingt quatre »,
« de quinze à vingt-quatre ans ». Le moteur attend des chiffres (« 2024 », « 15 à 24 ») pour
reconnaître une année ou une tranche d'âge.

Wolof (mots et règles écrits par KBD, 0009) : « ak » additionne (fukk ak ñett = 13) ; « fukk » après
des unités les multiplie (ñaar-fukk = 20, juróom-benn-fukk = 60) ; le suffixe « -i » (ñaari, ñeenti)
marque le multiplicateur devant téeméer, junni, milyoŋ, milyaar (ñaari junni = 2000) et reste une unité ailleurs
(ñeenti at = 4 ans) ; tirets ou espaces ; fanweer = 30 ; wirgil = virgule.

Prudence : un mot seul qui a un autre sens n'est jamais converti : « un », « une » (article), « benn »
(article), « dara » (rien), « tus », « fanweer » (mois) ; « pour cent » et « ci téeméer » restent tels
quels. Rien d'autre que les suites de mots-nombres n'est touché. Deux nombres reliés par « et » ou « ak »
restent deux nombres (« entre deux mille onze et deux mille vingt-deux » -> « entre 2011 et 2022 »).
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

# Wolof, formes sans accent (ñ -> n, ŋ -> ng), comme les compare _sans_accent
_WO_UNITES = {"tus": 0, "dara": 0, "benn": 1, "ben": 1, "naar": 2, "nett": 3, "natt": 3, "neent": 4,
              "nent": 4, "juroom": 5}
_WO_FUKK, _WO_FANWEER = "fukk", "fanweer"
_WO_MULTIPLES = {"teemeer": 100, "junni": 1000, "milyong": 10**6, "milyaar": 10**9}
_WO_LIAISONS = {"ak", "ag"}
_WO_SEULS_INTERDITS = {"benn", "ben", "dara", "tus", "fanweer"}


def _wo_mot(m: str) -> str | None:
    """Forme canonique d'un mot-nombre wolof (« ñaari » -> « naar »), ou None.
    Le suffixe -i (-y après un i) se met aussi sur fukk, fanweer, téeméer, junni, milyoŋ, milyaar
    devant un multiplicateur ou un nom : « fukki junni », « fanweeri junni », « junniy ton » (KBD)."""
    connus = (*_WO_UNITES, *_WO_MULTIPLES, _WO_FUKK, _WO_FANWEER)
    if m in connus:
        return m
    if m.endswith("i") and (m[:-1] in connus or m[:-1] + "n" in _WO_UNITES):  # ñaari, benni, fukki
        return m[:-1] if m[:-1] in connus else m[:-1] + "n"
    if m.endswith("iy") and m[:-1] in connus:  # junniy
        return m[:-1]
    return None


def _valeur_wo(mots: list[str]) -> int:
    total = courant = attente = 0  # attente : unités en cours (juróom-benn = 6)
    for m in mots:
        if m in _WO_UNITES:
            attente += _WO_UNITES[m]
        elif m == _WO_FUKK:
            courant += (attente or 1) * 10
            attente = 0
        elif m == _WO_FANWEER:
            courant += 30
        elif m == "teemeer":
            courant += (attente or 1) * 100
            attente = 0
        else:  # junni, milyoŋ, milyaar
            total += ((courant + attente) or 1) * _WO_MULTIPLES[m]
            courant = attente = 0
    return total + courant + attente


def _sans_accent(mot: str) -> str:
    mot = mot.lower().replace("ŋ", "ng")
    return unicodedata.normalize("NFKD", mot).encode("ascii", "ignore").decode()


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
    return re.findall(r"[^\W\d_]+|\s+|[^\s\w]|\d+|_", texte)


def en_chiffres(texte: str) -> str:
    """« en deux mille vingt-quatre » -> « en 2024 » ; « treize virgule deux » -> « 13,2 »."""
    jetons = _jetons(texte)
    sortie: list[str] = []
    i = 0
    while i < len(jetons):
        wo, j = _suite_wo(jetons, i)
        k = _apres_espaces(jetons, j)
        decimal = k < len(jetons) and _sans_accent(jetons[k]) == "wirgil"  # « tus wirgil juróom » = 0,5
        if wo and not (len(wo) == 1 and wo[0] in _WO_SEULS_INTERDITS and not decimal) and not (
                wo == ["teemeer"] and _avant(sortie) == "ci"):  # « ci téeméer » = pour cent
            nombre = str(_valeur_wo(wo))
            k = _apres_espaces(jetons, j)
            if k < len(jetons) and _sans_accent(jetons[k]) == "wirgil":
                apres, fin = _suite_wo(jetons, _apres_espaces(jetons, k + 1))
                if apres:
                    nombre, j = f"{nombre},{_valeur_wo(apres)}", fin
            sortie.append(nombre)
            i = j
            continue
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


def _apres_espaces(jetons: list[str], k: int) -> int:
    while k < len(jetons) and jetons[k].isspace():
        k += 1
    return k


def _suite_wo(jetons: list[str], i: int) -> tuple[list[str], int]:
    """Plus longue suite de mots-nombres wolof (tirets, espaces et « ak » internes admis)."""
    if i >= len(jetons) or jetons[i].isspace() or _wo_mot(_sans_accent(jetons[i])) is None:
        return [], i
    mots: list[str] = []
    fin = k = i
    while k < len(jetons):
        t = jetons[k]
        m = _wo_mot(_sans_accent(t))
        if m is not None:
            mots.append(m)
            fin = k + 1
        elif not (t.isspace() or t == "-" or (_sans_accent(t) in _WO_LIAISONS and mots
                                                and not _nouveau_nombre_wo(mots, jetons, k + 1))):
            break
        k += 1
    return mots, fin


def _nouveau_nombre_wo(mots: list[str], jetons: list[str], k: int) -> bool:
    """Après « ak » : le groupe qui suit commence-t-il un autre nombre ? Oui s'il porte un junni ou
    un milyoŋ au moins aussi grand que le dernier déjà lu (« ñaari junni ak fukk ak benn ak ñaari junni
    ak … » = deux années) ; « ñaari milyoŋ ak … ak ñetti junni » reste un seul nombre."""
    lus = [_WO_MULTIPLES[m] for m in mots if m in ("junni", "milyong", "milyaar")]
    if not lus:
        return False
    suivant = []
    while k < len(jetons):
        m = _wo_mot(_sans_accent(jetons[k]))
        if m is not None:
            suivant.append(m)
        elif not (jetons[k].isspace() or jetons[k] == "-"):
            break
        k += 1
    return any(_WO_MULTIPLES[m] >= lus[-1] for m in suivant if m in ("junni", "milyong", "milyaar"))


def _et_interne(jetons: list[str], k: int) -> bool:
    """« et » n'est à l'intérieur d'un nombre que devant un, une, onze (vingt et un, soixante et onze) :
    « deux mille onze et deux mille vingt-deux » reste deux nombres."""
    k = _apres_espaces(jetons, k)
    return k < len(jetons) and _sans_accent(jetons[k]) in ("un", "une", "onze")


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
        elif t.isspace() or t == "-" or (m == "et" and mots and _et_interne(jetons, k + 1)):
            pass  # liaison possible ; validée seulement si un mot-nombre suit
        else:
            break
        k += 1
    return mots, fin
