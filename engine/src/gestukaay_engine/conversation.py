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
                    "pourquoi", "hors_sujet", "impoli", "unite", "frequence", "producteur"]
CATEGORIES: tuple[str, ...] = Categorie.__args__


@cache
def _textes() -> dict[str, tuple[str, str]]:
    with (ICI / "conversation.csv").open(encoding="utf-8") as f:
        return {r["cle"]: (r["fr"], r["wo"]) for r in csv.DictReader(f, delimiter=";")}


def texte(cle: str, langue: str = "fr", **trous: str) -> str:
    fr, wo = _textes()[cle]
    t = (wo if langue == "wo" and wo.strip() else fr).format(**trous).strip()
    return t  # sigles écrits (« ANSD ») : la voix les épelle elle-même (parole._sigles)


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
    # #284 : « d'accord », « ok », « super » : tout le message (« ok, combien d'habitants à Thiès ? » reste une question)
    ("remerciement", re.compile(r"^ (d accord|ok|okay|ok merci|super|parfait|c est note|ca marche|entendu|cool|"
                                r"waaw|waw)( ge?stu?kaa?y)? $")),
    ("au_revoir", re.compile(r"^ (au revoir|a plus|a bientot|bye|ciao|ba beneen yoon) ")),
    ("a_propos", re.compile(r" (qui es tu|tu es qui|t es qui|qui t a (cree|fait|developpe)|tu es un robot|"
                            r"c est quoi gestukaay|qu est ce que gestukaay|d ou viennent tes (chiffres|donnees)) ")),
    ("langue", re.compile(r" (tu parles? (le )?wolof|repondre en wolof|reponds en wolof|parles tu wolof|"
                          r"quelles? langues?) ")),
    ("aide", re.compile(r"^ (aide moi|je peux (te )?demander quoi|que (sais|peux) tu faire|tu fais quoi|"
                        r"que puis je (te )?demander) ")),
    # « Lou gestukay meune def », « … lane leu gestukaay meune def » : formes de KBD (essai Telegram, 08/10)
    ("aide", re.compile(r" (lu|lou|lan|lane) (la |leu |le )?ge?stu?kaa?y (meune?|mene?|mun) def ")),
    # #273 : la fiche d'un indicateur nommé, lue dans le référentiel (unité, fréquence, producteur)
    ("unite", re.compile(r" (quelle unite|en quelle unite|dans quelle unite|unite (est )?(utilisee|de mesure)|"
                         r"se mesure en quoi|mesure en quoi) ")),
    ("frequence", re.compile(r" (a quelle frequence|quelle (est la )?frequence|tous les combien|"
                             r"(sont|est) (elles?|ils?) mis(es)? a jour|mises? a jour (quand|tous))")),
    ("producteur", re.compile(r" (qui (produit|publie|calcule|fournit|collecte)|produit ou publie|"
                              r"quel (organisme|service) (produit|publie)) ")),
    ("definition", re.compile(r"^ (c est quoi|qu est ce que?|que veut dire|ca veut dire quoi|definition( de| du)?|"
                              r"definis?|que signifie(nt)?) ")),
    # « Quelle est la différence entre le taux brut et le taux net ? », « Que signifie un Gini de 0,35 ? », « Comment
    # mesure-t-on les inégalités ? » : une explication de concept, sans zone ni période (recette du 08/10)
    ("definition", re.compile(r"^ (quelle est la difference entre|quelle difference (y a t il|existe t il) entre|"
                              r"que signifie|comment (mesure t on|mesurer|calculer|se calcule|on mesure)) ")),
    ("pourquoi", re.compile(r"^ (pourquoi|que pensez vous|qu en penses tu|tu penses que) ")),
    # « Comment expliquer… », « Quelles sont les conséquences de… », « … peut-elle expliquer… » : une analyse
    ("pourquoi", re.compile(r"^ (comment expliquer|quelles sont les (consequences|causes)|quels sont les (effets|facteurs))"
                            r" | peut (elle|il) expliquer | pourrai(t|ent) (elle|il|ils|elles)? ?(influencer|contribuer) ")),
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
    if cle == "definition" and t.startswith((" quelle", " comment")) and (zones_citees(question) or periodes_citees(question)):
        return None  # « la différence entre Dakar et Thiès en 2023 » : une comparaison de chiffres
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
            # rien après, encore une salutation (« Salam naka leu ») ou le nom du bot (« merci gëstukaay », #284) :
            # tout le message est la formule
            nom_seul = re.fullmatch(r" ge?stu?kaa?y ", _t(reste))
            return reste if len(reste) >= 3 and regles(reste) is None and not nom_seul else question
    return question


# « Quelles données as-tu sur l'agriculture ? » (recette du 09/10, #216) : les chiffres publiés de ce domaine,
# lus dans le référentiel (aucun LLM), au lieu de l'aide générique
_SUR_UN_DOMAINE = re.compile(r" (quelles?|quels?|tu as|vous avez|as tu|avez vous|y a t il) .*"
                             r"(donnees|chiffres|statistiques|stats|indicateurs|informations|infos)(?: \w+){0,3}? "
                             r"(sur|concernant|par rapport a|a propos de|en matiere de|dans|du domaine|de)"
                             r" (l |la |le |les |des |du )?(\w+)(?: au senegal| ci senegaal)? $")  # le domaine, et rien après
_DOMAINES_DITS = {"agriculture": "Agriculture", "agricoles": "Agriculture", "agricole": "Agriculture",
                  "sante": "Santé", "education": "Éducation", "ecole": "Éducation", "emploi": "Emploi et chômage",
                  "chomage": "Emploi et chômage", "prix": "Prix", "pauvrete": "Pauvreté", "peche": "Pêche",
                  "elevage": "Élevage", "energie": "Énergie", "electricite": "Énergie", "eau": "Eau",
                  "population": "Démographie", "demographie": "Démographie", "tourisme": "Tourisme",
                  "transport": "Transport", "transports": "Transport", "justice": "Justice", "genre": "Genre",
                  "migration": "Migration", "mines": "Mines", "habitat": "Habitat", "logement": "Habitat",
                  "economie": "Économie", "commerce": "Commerce extérieur", "telecommunications": "Télécommunications et TIC"}


def domaine_demande(question: str) -> str | None:
    """Le domaine dont l'usager demande les données disponibles, s'il est reconnu."""
    m = _SUR_UN_DOMAINE.search(_t(question))
    if not m or (m[3] == "de" and m[2] not in ("donnees", "indicateurs")):  # #237 : « les chiffres de la population »
        return None                                                          # demande la population, pas une liste
    return _DOMAINES_DITS.get(m[5])
