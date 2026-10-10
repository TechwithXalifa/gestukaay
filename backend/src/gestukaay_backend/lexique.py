"""Lexique grand public et wolof (back-office, V1.1, #23).

Les usagers disent « les mamans », « l'argent des ménages », « le prix du sac de riz » : des mots que le
moteur ne relie pas toujours au bon indicateur. Le lexique permet à l'équipe (le linguiste pour le wolof,
décision 0009) d'ajouter une expression et sa forme comprise par le moteur, sans attendre un déploiement :
« les mamans » -> « les femmes ».

Seules les entrées VALIDÉES s'appliquent, avant l'appel au moteur ; l'usager voit toujours sa question telle
qu'il l'a écrite. Rien ne change dans le moteur ni dans le socle : c'est une réécriture de la question, réglée
par l'équipe, exportable en CSV pour que KBD l'intègre ensuite au moteur.

La comparaison ignore la casse et les accents (« ménages » = « menages ») et ne prend que des mots entiers ;
l'expression la plus longue l'emporte (« taux de chômage des jeunes » avant « chômage »).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

QUESTION_MAX = 300  # AskRequest.question
# Une lettre de l'expression accepte ses variantes accentuées dans la question (français et wolof)
_VARIANTES = {
    "a": "aàâäá", "e": "eéèêë", "i": "iîïí", "o": "oôöó", "u": "uùûüú", "c": "cç", "n": "nñ", "y": "yÿ",
}


def sans_accents(texte: str) -> str:
    """Minuscules sans accents ; le ŋ wolof, qui ne se décompose pas, reste tel quel."""
    t = unicodedata.normalize("NFKD", texte.lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch))


@lru_cache(maxsize=512)
def _coeur(expression: str) -> str:
    """Le motif d'une expression, sans les bornes : sans casse ni accents, espaces et apostrophes souples."""
    morceaux: list[str] = []
    for ch in sans_accents(expression.strip()):
        if ch.isspace() or ch in "'’-":
            if not morceaux or morceaux[-1] != r"[\s'’-]+":
                morceaux.append(r"[\s'’-]+")
        elif ch in _VARIANTES:
            morceaux.append(f"[{_VARIANTES[ch]}]")
        else:
            morceaux.append(re.escape(ch))
    return "".join(morceaux)


def motif(expression: str) -> re.Pattern:
    """Motif d'une expression, en mots entiers."""
    return re.compile(rf"(?<!\w){_coeur(expression)}(?!\w)", re.IGNORECASE)


@dataclass(frozen=True)
class Entree:
    id: str
    expression: str
    remplacement: str


def appliquer(question: str, entrees: list[Entree]) -> tuple[str, list[Entree]]:
    """La question réécrite et les entrées appliquées, en un seul passage : un remplacement n'est jamais relu
    (« chômage des jeunes » -> « taux de chômage des 15-24 ans » ne repasse pas par « chômage »). Une réécriture
    qui dépasserait la longueur permise est abandonnée : la question part telle quelle."""
    if not entrees:
        return question, []
    ordre = sorted(entrees, key=lambda x: -len(x.expression))  # à la même position, la plus longue l'emporte
    tout = re.compile(r"(?<!\w)(?:" + "|".join(f"(?P<e{i}>{_coeur(e.expression)})" for i, e in enumerate(ordre))
                      + r")(?!\w)", re.IGNORECASE)
    appliquees: dict[int, Entree] = {}

    def remplacer(m: re.Match) -> str:
        i = int(m.lastgroup[1:])
        appliquees[i] = ordre[i]
        return ordre[i].remplacement  # pris tel quel, sans référence de groupe

    texte = tout.sub(remplacer, question)
    if len(texte) > QUESTION_MAX:
        return question, []
    return texte, list(appliquees.values())
