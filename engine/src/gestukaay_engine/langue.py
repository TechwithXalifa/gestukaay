"""Langue d'une question transcrite : français ou wolof (premier pas de #24, choix KBD sur #125).

Le service de transcription ne dit pas la langue : sans elle, une question dite en français au micro
partait au moteur comme du wolof. On compte les petits mots de chaque langue ; un mot interrogatif
wolof (ñaata, ndax, ban…) suffit à trancher, et le wolof l'emporte en cas d'égalité.

Limite connue : une question « wolof » faite uniquement de mots français (« Taux chomage en 2030 »)
est lue comme du français. Mesuré sur le jeu de test (177 questions) et les 62 notes vocales.
"""

from __future__ import annotations

import re
import unicodedata

_FR = {
    "le", "la", "les", "de", "des", "du", "d", "l", "est", "sont", "combien", "quel", "quelle", "quels",
    "quelles", "en", "au", "aux", "et", "pour", "dans", "par", "sur", "entre", "y", "a", "t", "il",
    "elle", "on", "qui", "que", "qu", "plus", "moins", "avec", "ou", "habitants", "nombre", "personnes",
    "menages", "annee", "part", "pays", "region", "ville", "depuis", "ce", "cette", "se", "ont",
    # conversation (0033) : « comment tu vas », « ça va », « merci », « qui es-tu »…
    "comment", "tu", "vas", "va", "ca", "merci", "bonjour", "bonsoir", "salut", "vous", "je", "moi",
    "toi", "es", "suis", "peux", "pouvez", "pourquoi", "quoi", "veut", "dire", "revoir", "aide", "parles",
    "parlez", "fait", "faire", "bien", "oui", "non", "un", "une", "mon", "ton", "votre", "avez", "as",
}
_WO = {
    "ci", "ak", "ag", "nit", "nu", "ni", "yi", "bi", "ba", "bu", "yu", "la", "na", "dekk", "deuk", "ko",
    "am", "amul", "xale", "jigeen", "goor", "atum", "at", "diggante", "gena", "geuna", "epp", "nekk",
    "nek", "dafa", "dafay", "dina", "daa", "doon", "yepp", "yeup", "limu", "askanu", "tamit", "nak", "li",
    "lu", "dem", "ren", "daaw", "tey", "ndaw", "mag", "waa", "sunu", "seen", "yokk", "yokku", "wanniku",
}
# Mots qui suffisent : interrogatifs et marqueurs wolof (formes sans accent, ñ -> n)
_WO_FORTS = {"naata", "nata", "niata", "gnata", "gnaata", "nyata", "nyaata", "ndax", "ban", "lan", "naka", "noo",
             "nio", "nioy", "nooy", "mooy", "moy"}


def _mots(texte: str) -> list[str]:
    t = unicodedata.normalize("NFKD", texte.lower()).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z]+", t)


def detecter(texte: str) -> str:
    """« fr » ou « wo »."""
    mots = _mots(texte)
    if any(m in _WO_FORTS for m in mots):
        return "wo"
    fr, wo = sum(m in _FR for m in mots), sum(m in _WO for m in mots)
    if not fr and not wo:  # « asdkjh qwe » : aucun mot connu, le français par défaut (SAN, #156)
        return "fr"
    return "fr" if fr > wo else "wo"
