"""Ce que l'on peut trouver dans une question SANS LLM (issue #10) : zones citées,
périodes citées, et les indicateurs candidats.

Le LLM ne choisit ensuite qu'un NUMÉRO parmi ces candidats : il n'écrit jamais
un code d'indicateur ni de zone, donc il ne peut pas en inventer.

  - zones : les mots de la question passés au référentiel des zones du socle
    (« Thiès », « Cees », « Dpt Mbacké », « IA Kolda », « Ndakaaru ») ;
  - candidats : recherche lexicale BM25 dans les libellés FR / WO et les noms
    de jeux des indicateurs, élargie par un petit vocabulaire FR / WO (amorce
    du lexique métier #23).
"""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import cache

from gestukaay_socle.indicateurs import Indicateur, indicateurs, nom_du_jeu
from gestukaay_socle.zones import normaliser, resoudre

# Mots vides FR et WO : n'aident pas à trouver l'indicateur
_VIDES = {
    "le", "la", "les", "l", "de", "des", "du", "d", "un", "une", "et", "ou", "a", "au", "aux",
    "en", "dans", "par", "pour", "sur", "avec", "sans", "est", "sont", "quel", "quelle", "quels",
    "quelles", "combien", "y", "il", "elle", "ce", "cet", "cette", "ces", "qui", "que", "quoi",
    "on", "ont", "entre", "plus", "moins", "tres", "niveau", "ci", "ak", "ba", "bi", "yi", "gi",
    "ji", "wi", "mi", "si", "lan", "ban", "nak", "na", "ndax", "naka", "mooy", "moy", "lay", "di",
    "nio", "nioy", "noo", "ngi", "moo", "epp", "bou", "bu", "yu", "ndaw",
    "personne", "personnes", "temp", "temps", "fera", "fait", "faire", "demain",
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos", "votre", "vos", "leur", "leurs",
    "euh", "bon", "voila", "voici", "hein", "bah", "trop",
    "waa", "man", "tay", "dama", "xiif", "lii", "mbaa", "diamm", "tamit",
    # le pays de toutes les questions : « la population sénégalaise » ne cherche pas la nationalité « Sénégalaise »
    # (recette du 08/10 : « Sénégalaise : 25 160 » pour « de combien la population sénégalaise a-t-elle augmenté »)
    "senegal", "senegalais", "senegalaise", "senegalaises", "senegaal",
}

# Amorce du lexique métier (#23) : mot de la question -> mots des libellés.
# Formes normalisées (minuscules, sans accents), FR et WO dans les deux écritures.
SYNONYMES: dict[str, tuple[str, ...]] = {
    "habitants": ("population",), "habitant": ("population",), "peuplee": ("population",),
    # « askan » : le mot du libellé wolof de la population (KBD). Sans lui, « nit », présent dans le seul
    # libellé wolof des prisons, faisait répondre les détenus à « Ñaata nit ñoo dëkk Kaolack ? » (07/10)
    "nit": ("population", "askan"), "nitt": ("population", "askan"), "deuk": ("population", "askan"),
    "dekk": ("population", "askan"),
    "askan": ("population",), "askanu": ("population",), "jigeen": ("population", "feminin"),
    "chomeurs": ("chomage",), "liggeey": ("chomage",), "ligeey": ("chomage",), "amul": ("chomage",),
    "pauvre": ("pauvrete",), "pauvres": ("pauvrete",),
    "coute": ("prix",), "cout": ("prix",), "njeg": ("prix",), "diar": ("prix",), "jar": ("prix",),
    "coutait": ("prix",), "coutent": ("prix",), "coutaient": ("prix",),
    "ceeb": ("riz",), "thieb": ("riz",), "dugub": ("mil",),
    "inflation": ("indice", "prix", "consommation"), "ihpc": ("indice", "prix", "consommation"),
    # l'école n'est pas le taux de scolarisation : « Combien d'écoles ? » donnait 84,7 % (KBD, 08/10) ; étudier = jàng
    "lekool": ("ecole",), "ekool": ("ecole",), "primaire": ("elementaire",),
    "vaccin": ("vaccines",), "vaccins": ("vaccines",), "vaccination": ("vaccines",),
    "electricite": ("eclairage", "electricite"), "courant": ("eclairage", "electricite"),
    "kouran": ("eclairage", "electricite"),
    "deces": ("mortalite",), "faatu": ("mortalite",), "mourir": ("mortalite",),
    "enfants": ("enfants",), "xale": ("enfants",), "fecondite": ("fecondite", "synthetique"),
    "doom": ("enfants",),  # doom = enfant (de quelqu'un) : « ñaata doom la jigéen di am » = l'ISF (recette 08/10)
    "gaz": ("hydrocarbures", "nm3"), "petrole": ("hydrocarbures", "baril"),
    "inegalites": ("gini",), "pib": ("produit", "interieur", "brut"),
    "telephone": ("telephonie", "mobile"), "portable": ("telephonie", "mobile"), "telefon": ("telephonie", "mobile"),
    "touristes": ("arrivees", "residents"), "prison": ("emprisonnees",), "kaso": ("emprisonnees",),
    "prisonniers": ("emprisonnees",), "detenus": ("emprisonnees",), "detenues": ("emprisonnees",),
    "detenu": ("emprisonnees",), "carcerale": ("emprisonnees",),
    "poisson": ("captures", "halieutiques"), "peche": ("captures", "halieutiques"), "jen": ("captures",),
    "voitures": ("vehicule",), "vehicules": ("vehicule",), "woto": ("vehicule",),
    "crimes": ("criminalite",), "salaire": ("salaire",), "payooru": ("salaire",),
    "urbaine": ("urbanisation",), "dekkuwaay": ("urbanisation",), "cereales": ("cereales",),
    "malnutrition": ("retard", "croissance"), "robinet": ("robinet",),
    "riz": ("riz", "cereales"), "mil": ("mil", "cereales"), "mais": ("cereales",), "sorgho": ("cereales",),
    "jeunes": ("population", "age"), "geej": ("captures", "halieutiques"), "nappkat": ("captures", "peche"),
    "debarquee": ("captures",), "debarquements": ("captures",),
    "vivent": ("population",), "vivre": ("population",), "vit": ("population",),
    # Vocabulaire wolof validé par KBD (#23, 0009), formes sans accents. « ñakk » (vaccin) et « ñàkk »
    # (manquer, pauvreté) s'écrivent tous deux « nakk » une fois les accents retirés : les deux notions
    # sont proposées, le reste de la phrase tranche (« ñàkk liggéey » = chômage, « xale yi am ñakk »).
    "nakk": ("pauvrete", "vaccines"), "ndool": ("pauvrete",), "tolluwaay": ("taux",),
    "tolluwaayu": ("taux",), "toluwaay": ("taux",), "toluwaayu": ("taux",),
    "mbej": ("eclairage", "electricite"), "kurang": ("eclairage", "electricite"),
    "njang": ("scolarisation",), "jang": ("scolarisation", "njang"),  # jàng = étudier (KBD, 07/10, remarque SAN)
    "dee": ("mortalite",), "deeg": ("mortalite",), "yamadi": ("gini",),  # formes de KBD, 08/10
    "nakkug": ("vaccines",),  # ñakkug xale yi : la vaccination des enfants (KBD, 08/10)
    "ndaw": ("population", "age"),
    "goor": ("population", "masculin"), "tej": ("emprisonnees",), "napp": ("captures", "peche"),
    "ndab": ("vehicule",), "vootuur": ("vehicule",),
    "ker": ("menages",), "keur": ("menages",),  # kër = ménage (KBD, 06/10), graphie WhatsApp « keur »
}

_MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
         "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
         # mois en wolof, formes de KBD (questions du 08/10) : seulement celles qu'il a écrites
         "samwiye": 1, "fewriye": 2, "suweng": 6, "sulet": 7, "desambar": 12}
# « weeru mars atum 2026 », « ñaareelu ñetti weer yi ci atum 2023 » (KBD, 08/10) : ramenés à « mars 2026 », « t2 2023 » ;
# « ñetti » peut déjà être devenu « 3 » (nombres en lettres convertis avant la compréhension, #153)
_DATES_WO = ((re.compile(r"\bweeru "), ""),
             (re.compile(r"\b(" + "|".join(_MOIS) + r") (?:ci )?atum (?=(?:19|20)\d\d\b)"), r"\1 "),
             (re.compile(r"\b(?:netti|3) weer yu njekk (?:yu |yi |ci |atum )*(?=(?:19|20)\d\d\b)"), "t1 "),
             (re.compile(r"\bnaareelu (?:netti|3) weer (?:yu |yi |ci |atum )*(?=(?:19|20)\d\d\b)"), "t2 "),
             (re.compile(r"\b(?:netti|3) weer yu mujj (?:yu |yi |ci |atum )*(?=(?:19|20)\d\d\b)"), "t4 "))


def texte_normalise(texte: str) -> str:
    """Normalisé, apostrophes ouvertes : « d'habitants » -> « d habitants ». La ponctuation collée
    (« Thiès? », « Kaolack! ») est détachée : c'est ainsi qu'on tape sur une messagerie et que les
    modèles de transcription écrivent. Pas dans `normaliser` : il fabrique aussi les codes."""
    # « ŋ » n'a pas d'équivalent ASCII : sans ce remplacement, « kuraŋ » devenait « kura » (KBD, 06/10)
    texte = texte.replace("ŋ", "ng").replace("Ŋ", "Ng")
    return normaliser(re.sub(r"['’`?!;:\"]", " ", texte))


def forme(m: str) -> str:
    """Pluriel simple retiré : « vaccins » -> « vaccin », « touristes » -> « touriste »."""
    return m[:-1] if len(m) > 4 and m.endswith(("s", "x")) else m


def mots(texte: str) -> list[str]:
    """Mots utiles, normalisés, au singulier."""
    return [forme(m) for m in texte_normalise(texte).split() if m not in _VIDES and len(m) > 1]


_SYN = {forme(k): tuple(forme(v) for v in vs) for k, vs in SYNONYMES.items()}


# --------------------------------------------------------------------------
# Zones et périodes citées
# --------------------------------------------------------------------------

def zones_citees(question: str) -> list[str]:
    """Codes des zones citées, dans l'ordre. Les groupes de 4 mots à 1 mot sont
    essayés, du plus long au plus court (« departement de mbacke » avant « mbacke »)."""
    t = texte_normalise(question).replace("academies", "academie").replace("nationale", "national")
    m = t.split()
    # « académies de Kolda et de Ziguinchor » : le niveau cité vaut pour tous les noms qui suivent
    niveau = "academie" if re.search(r"\b(academie|ia)\b", t) else None
    trouvees: list[str] = []
    i = 0
    while i < len(m):
        for n in (4, 3, 2, 1):
            if i + n <= len(m) and (code := resoudre(" ".join(m[i:i + n]), niveau)):
                if code not in trouvees:
                    trouvees.append(code)
                i += n
                break
        else:
            i += 1
    return trouvees


# « à Touba », « ci Touba », « la ville de Thiès », « sur la Casamance » : un lieu nommé hors du référentiel
_LIEU = re.compile(r"\b(?:à|a|au|aux|dans|ci|sur|en)\s+(?:la\s+)?(?:ville\s+(?:de\s+)?)?([A-ZÉÈÎ][\w'’-]+)")
# « la commune de Thiès » est une ville, pas la région (recette du 09/10, #205 : la région était servie)
_VILLE = re.compile(r"\b(?:ville|commune)\s+(?:de\s+)?([A-ZÉÈÎa-zéèî][\w'’-]+)", re.IGNORECASE)
_PAS_UN_LIEU = {"sénégal", "senegal", "senegaal", "ndakaaru", "la", "le", "les", "l"}
# Un mot à majuscule au milieu de la phrase, inconnu du référentiel et du vocabulaire des indicateurs, est un
# lieu (« Population de Paris », « du Fouta ») : en règles, il devenait le Sénégal (recette du 08/10). Pas les
# sigles (PIB, ANSD, RGPH), ni ces mots que l'on écrit souvent avec une majuscule.
_MAJUSCULE = re.compile(r"(?<![.?!]\s)(?<!^)\b([A-ZÉÈÎ][a-zéèêëàâîïôöûüç'’-]{2,})")
_PAS_UN_LIEU_MAJ = {"merci", "svp", "stp", "bonjour", "bonsoir", "salut", "salam", "monsieur", "madame",
                    "wolof", "francais", "français", "republique", "république", "etat", "état", "gouvernement",
                    "assemblee", "assemblée", "president", "président", "ministere", "ministère", "banque",
                    "bceao", "ansd", "nationale", "national", "total", "afrique"}
# Hors du Sénégal sans nom propre : « dans le monde », « en Afrique »
_AILLEURS = {"monde", "mondial", "mondiale", "afrique", "africain", "europe", "etranger", "international",
             "internationale", "france", "gambie", "mali", "mauritanie", "guinee", "maroc", "chine", "usa",
             # « se compare-t-il à celui du Mali / de la Côte d'Ivoire / de l'UEMOA / des pays voisins » (recette 08/10)
             "ivoire", "uemoa", "cedeao", "voisins", "burkina", "niger", "nigeria", "ghana", "benin", "togo"}


def _debut_de_zone(nom: str, question: str) -> bool:
    """« Sant » dans « à Sant Louis », « St » dans « St-Louis » : le début d'un nom de zone en plusieurs mots."""
    t, n = texte_normalise(question).split(), texte_normalise(nom).split()
    return bool(n) and any(t[i] == n[0] and any(resoudre(" ".join(t[i:i + k])) for k in (2, 3, 4))
                           for i in range(len(t)))


def lieux_inconnus(question: str) -> list[str]:
    """Lieux cités mais absents du référentiel : ils ne doivent jamais devenir « le Sénégal ».
    « la ville de Thiès » n'est pas la région de Thiès : signalée aussi (réponse approchée, #12)."""
    out = [f"ville de {m[1]}" for m in _VILLE.finditer(question)]
    for m in _LIEU.finditer(question):
        nom = m[1]
        gentile = re.search(r"(ais|aise|ien|ienne|ain|aine)s?$", nom.lower())  # Sénégalais, Kaolackois…
        if (nom.lower() not in _PAS_UN_LIEU and not gentile and not resoudre(nom) and not any(nom in o for o in out)
                and not _debut_de_zone(nom, question)):
            out.append(nom)
    deja = {normaliser(o) for o in out}
    vocab = index().idf
    for m in _MAJUSCULE.finditer(question):
        nom = m[1].rstrip("'’-")
        n = normaliser(nom)
        if (n in deja or n in _PAS_UN_LIEU or n in _PAS_UN_LIEU_MAJ or n in _VIDES or resoudre(nom) or forme(n) in vocab
                or n in vocab or n in _SYN or n in _MOIS or any(n in d for d in deja) or _debut_de_zone(nom, question)):
            continue
        out.append(nom)
        deja.add(n)
    for mot in texte_normalise(question).split():
        if mot in _AILLEURS and mot not in deja:
            out.append(mot)
            deja.add(mot)
    # Lieux déclarés dans rattachements.csv, où qu'ils soient : « Ñaata nit ñoo dëkk Tuubaa ? » n'a pas de
    # préposition française, mais Touba ne doit jamais devenir le Sénégal.
    t = f" {texte_normalise(question)} "
    deja = {texte_normalise(o) for o in out}
    for terme in _lieux_rattaches():
        if f" {terme} " in t and terme not in deja and not any(terme in d for d in deja):
            out.append(" ".join(m if m in ("de", "du") else m.capitalize() for m in terme.split()))
    return out


@cache
def _lieux_rattaches() -> tuple[str, ...]:
    """Termes de lieu de socle/referentiels/rattachements.csv (touba, tuubaa, richard toll…), normalisés."""
    from gestukaay_socle.indicateurs import REFERENTIELS

    with (REFERENTIELS / "rattachements.csv").open(encoding="utf-8") as f:
        return tuple(sorted({texte_normalise(r["terme"]) for r in csv.DictReader(f, delimiter=";") if r["type"] == "lieu"},
                            key=len, reverse=True))


# Classement « le plus faible » (sens croissant), sur une question normalisée. « moins de » suivi d'un
# nombre est une tranche (« enfants de moins de 5 ans »), pas un sens de tri (FR-045).
ORDRE_ASC = re.compile(r"\b(le|la|les) (moins|plus bas(se)?|plus faible(s)?)\b|\bmoins d[e']\b(?!\s*\d)"
                       r"|\bgena (neew|tuuti)\b"  # wolof (KBD) : « moo gëna néew / tuuti » = le moins
                       # « gëna ñàkk kuraŋ » = manquer le plus d'électricité = l'accès le plus faible (KBD, 06/10).
                       # Pas « gëna ñàkk » seul (le plus pauvre) ni « gëna ñàkk liggéey » (chômage le plus élevé) :
                       # là, l'indicateur mesure déjà le manque.
                       r"|\bgena nakk (kurang|kuran|kouran|courant|mbej)\b")


# Années dites sans chiffre (recette du 08/10) : « l'année dernière » donnait le T1 2026, « l'année prochaine »
# la dernière valeur publiée au lieu d'un refus de projection. Référence : l'année en cours (resolution.py).
_RELATIVES = [
    (re.compile(r"\b(l )?(annee|an) (derniere|dernier|passee|passe)\b"), -1),
    (re.compile(r"\b(l )?(annee|an) (prochaine|prochain)\b"), 1),
    (re.compile(r"\bcette annee\b|\bcette annee ci\b"), 0),
]
_IL_Y_A = re.compile(r"\bil y a (\d{1,2}) ans?\b")
_DANS = re.compile(r"\bdans (\d{1,2}) ans?\b")


_RANG = {"premier": 1, "1er": 1, "1ere": 1, "deuxieme": 2, "second": 2, "seconde": 2, "2e": 2, "2eme": 2,
         "troisieme": 3, "3e": 3, "3eme": 3, "quatrieme": 4, "4e": 4, "4eme": 4, "dernier": 4}
_TRIMESTRE = re.compile(r"\b(?P<r1>" + "|".join(_RANG) + r")(?: (?:et|au|a) (?:le |du )?(?P<r2>" + "|".join(_RANG)
                        + r"))? trimestres? (?:de |du |en )?(?P<an>(?:19|20)\d\d)\b")
_DEUX_MOIS = re.compile(r"\b(?P<m1>" + "|".join(_MOIS) + r") (?:et|a|au|ak) (?:le |la |l )?(?P<m2>" + "|".join(_MOIS)
                        + r") (?P<an>(?:19|20)\d\d)\b")


def periodes_citees(question: str) -> list[str]:
    """« mars 2025 » -> 2025-03 ; « 2023 » -> 2023 ; « T2 2024 » -> 2024-T2. Dans l'ordre.
    « l'année dernière », « il y a 5 ans », « l'an prochain » : l'année correspondante.
    « le premier trimestre 2026 » -> 2026-T1 ; « entre février et mars 2026 » -> 2026-02, 2026-03 (recette 08/10)."""
    from .resolution import ANNEE_EN_COURS

    t = texte_normalise(question)
    for motif, par in _DATES_WO:  # mois et trimestres en wolof (KBD) ramenés aux formes lues ci-dessous
        t = motif.sub(par, t)
    trouves: list[tuple[int, str]] = []
    pris: list[tuple[int, int]] = []  # zones du texte déjà lues, pour ne pas relire « 2026 » seul

    def libre(a: int, b: int) -> bool:
        return all(b <= x or a >= y for x, y in pris)

    for m in _TRIMESTRE.finditer(t):
        trouves.append((m.start(), f"{m['an']}-T{_RANG[m['r1']]}"))
        if m["r2"]:
            trouves.append((m.start() + 1, f"{m['an']}-T{_RANG[m['r2']]}"))
        pris.append(m.span())
    for m in _DEUX_MOIS.finditer(t):
        if libre(*m.span()):
            trouves += [(m.start(), f"{m['an']}-{_MOIS[m['m1']]:02d}"), (m.start() + 1, f"{m['an']}-{_MOIS[m['m2']]:02d}")]
            pris.append(m.span())
    for motif, d in _RELATIVES:
        if r := motif.search(t):
            trouves.append((r.start(), str(ANNEE_EN_COURS + d)))
    trouves += [(m.start(), str(ANNEE_EN_COURS - int(m[1]))) for m in _IL_Y_A.finditer(t)]
    trouves += [(m.start(), str(ANNEE_EN_COURS + int(m[1]))) for m in _DANS.finditer(t)]
    for m in re.finditer(r"\b(?:(?P<mois>" + "|".join(_MOIS) + r")\s+)?(?:(?P<t>t[1-4])\s+)?"
                         r"(?P<an>(?:19|20)\d\d)\b", t):
        if not libre(*m.span()):
            continue
        if m["mois"]:
            trouves.append((m.start(), f"{m['an']}-{_MOIS[m['mois']]:02d}"))
        elif m["t"]:
            trouves.append((m.start(), f"{m['an']}-T{m['t'][1]}"))
        else:
            trouves.append((m.start(), m["an"]))
    out: list[str] = []
    for _, v in sorted(trouves):
        if v not in out:
            out.append(v)
    return out


# Une question d'évolution (recette du 08/10 : 33 réponses sur 170 ne donnaient qu'une valeur) : deux périodes
EVOLUTION = re.compile(
    r"\bevolu|\btendance|\b(augment|diminu|baiss|progress|recul|amelior|degrad)\w*|\bdepuis\b"
    r"|\bapres (?:la |le |l )?(?:(?:19|20)\d\d|pandemie|covid)|\bqu il y a\b|\blong terme\b|\bhistorique\b"
    r"|\bd (?:un|une) (?:mois|trimestre|an|annee) (?:a|sur) l autre\b"
    r"|\b(?:\d+|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|quinze|vingt|trente|quarante) (?:dernieres|derniers)"
    r" (?:annees|ans|mois|trimestres)\b|\bdernieres decennies\b|\bsur (?:pres de |plus de )?(?:\d+|dix|vingt|trente|quarante) ans\b")
_NOMBRES = {"deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
            "quinze": 15, "vingt": 20, "trente": 30, "quarante": 40}


def fenetre_annees(question: str) -> int | None:
    """« au cours des dix dernières années », « sur près de quarante ans » -> 10, 40 ; « dernières décennies » -> 30."""
    t = texte_normalise(question)
    if m := re.search(r"\b(\d+|" + "|".join(_NOMBRES) + r") (?:dernieres|derniers) (?:annees|ans)\b", t) or \
            re.search(r"\bsur (?:pres de |plus de )?(\d+|" + "|".join(_NOMBRES) + r") ans\b", t):
        return int(m[1]) if m[1].isdigit() else _NOMBRES[m[1]]
    return 30 if re.search(r"\bdernieres decennies\b", t) else None


# « Quel mois a enregistré le plus d'arrivées en 2018 ? », « À quelle période le riz était-il le moins cher ? »,
# « En quelle année les captures ont-elles atteint leur niveau le plus élevé ? » (recette du 08/10)
_EXTREMUM = re.compile(r"\b(?:quel|quelle|a quel|a quelle|en quel|en quelle) (?:mois|annee|trimestre|periode)\b")
_EXTREMUM_BAS = re.compile(r"\b(?:le |la |les )?(?:moins|plus bas(?:se)?|plus faibles?|minimum)\b")


def extremum(question: str) -> str | None:
    """« max » ou « min » si la question cherche la période du plus haut ou du plus bas niveau d'une série."""
    t = texte_normalise(question)
    if not _EXTREMUM.search(t) or not re.search(r"\b(plus|moins|maximum|minimum|record)\b", t):
        return None
    return "min" if _EXTREMUM_BAS.search(t) else "max"


def fenetre_periodes(question: str) -> int | None:
    """« au cours des douze derniers mois », « des quatre derniers trimestres » -> 12, 4 (périodes de la série)."""
    t = texte_normalise(question)
    m = re.search(r"\b(\d+|douze|" + "|".join(_NOMBRES) + r") (?:derniers|dernieres) (?:mois|trimestres)\b", t)
    return None if not m else 12 if m[1] == "douze" else int(m[1]) if m[1].isdigit() else _NOMBRES[m[1]]


def est_evolution(question: str) -> bool:
    return bool(EVOLUTION.search(texte_normalise(question)))


def milieu_cite(texte: str) -> str | None:
    """« rural » ou « urbain » si le texte (normalisé) cite un milieu."""
    # « gox-goxaan yi », « all bi » = le milieu rural ; « dëkk yi » = les villes (KBD, 06/10 et 08/10)
    if re.search(r"\b(ruraux|rurales?|rural|goxaan|all bi)\b", texte):
        return "rural"
    if re.search(r"\b(urbains?|urbaines?|dekk yi)\b", texte):
        return "urbain"
    return None


_RATIO = re.compile(r"\b(pour|par) (1 ?000|10 ?000|100 ?000|mille|cent mille|cent) (habitants?|naissances?|personnes?"
                    r"|femmes?|enfants?)\b|\bpar (habitant|tete|personne)\b|\bdensite\b")
# les formes de ratio elles-mêmes, pas un « par » de ventilation (« par région », « par sexe » : revue de SAN sur #162)
_RATIO_PUBLIE = re.compile(r"\b(pour|par) (1 ?000|10 ?000|100 ?000|mille|cent mille|cent|habitants?|tete|personnes?"
                           r"|naissances?|femmes?|enfants?)\b|%|\b(hbt|densite|pourcentage|taux|proportion|ratio)\b")  # pas « hôpitaux »


def ratio_non_publie(code: str, question: str) -> bool:
    """La question demande un ratio (« pour 10 000 habitants », « par habitant », « densité ») que
    l'indicateur ne publie pas tel quel : le servir serait donner un autre chiffre."""
    if not _RATIO.search(texte_normalise(question)):
        return False
    ind = indicateurs().get(code)
    if ind is None:
        return False
    return not _RATIO_PUBLIE.search(normaliser(f"{ind.libelle_fr} {ind.unite_affichee or ind.unite}"))


# Recette du 09/10 : une négation (« n'ont pas accès à l'eau ») ou une variation (« l'inflation ») demande autre chose
# que ce que l'indicateur publie (la part qui A accès, le niveau d'un indice)
_NEGATION = re.compile(r"\b(n ont pas|n a pas|ne sont pas|n est pas|ne disposent pas|ne dispose pas|n ont aucun"
                       r"|sans acces|prives? d|privees? d)\b")
_INFLATION = re.compile(r"\binflation\b")


def mesure_inverse(code: str, question: str) -> bool:
    """#206, #207 : la question demande l'inverse ou la variation de ce que l'indicateur publie. Le servir
    donnerait un autre chiffre (85,9 % des ménages qui ONT accès, pour « n'ont pas accès ») ; le calculer
    (100 − x) fabriquerait un chiffre. Il est proposé en suggestion, comme un ratio non publié."""
    ind = indicateurs().get(code)
    if ind is None:
        return False
    t, libelle = texte_normalise(question), texte_normalise(ind.libelle_fr)
    if _INFLATION.search(t) and not re.search(r"\b(inflation|glissement)\b", libelle):
        return True
    m = _NEGATION.search(t)
    if not m or re.search(r"\b(sans|non|pas|aucun|prives?|privees?)\b", libelle):
        return False
    if m[1] in ("ne sont pas", "n est pas"):  # un état (« qui ne sont pas diplômées ») : la population, sauf s'il
        return _porte_sur_la_mesure(t[m.end():], libelle)  # est ce que l'indicateur mesure (« pas scolarisés »)
    return True  # un accès, une possession (« n'ont pas accès », « ne disposent pas ») : toujours la mesure (#206)


_VIDES_NEGATION = {"d", "de", "du", "des", "l", "la", "le", "les", "au", "aux", "un", "une", "a", "en", "encore"}


def _porte_sur_la_mesure(apres: str, libelle: str) -> bool:
    """#238 : « chômage des personnes qui ne sont pas diplômées » nie la population, pas la mesure ; « enfants qui
    ne sont pas scolarisés » nie bien la mesure (la scolarisation). L'état nié compte si l'un des mots qui le suivent
    est dans le libellé ; sans mot à comparer, il compte (prudence : un refus plutôt qu'un chiffre inverse)."""
    mots = [w for w in apres.split()[:7] if w not in _VIDES_NEGATION][:3]
    if not mots:
        return True
    du_libelle = {w[:5] for w in libelle.split() if len(w) >= 3}
    return any(w[:5] in du_libelle for w in mots)


_SANS_EMPLOI = re.compile(r"\bsans (emploi|travail|boulot|job)\b", re.IGNORECASE)


# Recette de SAN du 09/10 : des données publiées jamais trouvées. Des tournures exactes, ramenées aux mots du
# libellé publié (des synonymes larges faisaient servir des voisins : « dépensent les ménages » -> le savon de
# ménage). Rien d'autre n'est touché.
_TOURNURES = [
    # #201 : « le nombre de femmes à Dakar » -> population (RGPH-5), sexe féminin
    (re.compile(r"\b(?:le )?(?:nombre d(?:e |')|combien d(?:e |'))(femmes|hommes)\b(?=\s+(?:à|a|au|aux|en|dans|du|de la)\s+"
                r"[A-ZÉÈÎa-zéèîñ' -]+(?:\s+en\s+\d{4})?\s*[?.!]?\s*$)", re.IGNORECASE),
     lambda m: f"la population des {m[1].lower()}"),
    # #209 : la dépense moyenne publiée est la consommation moyenne par tête (EHCVM, jcvcajc)
    # ... mais pas pour un poste précis (#236 : « en électricité », « pour la santé », « d'eau » -> refus, jamais le total)
    (re.compile(r"\b(?:combien\s+)?d[ée]pens(?:ent|e|es)\s+(?:moyennes?\s+)?(?:les\s+|des\s+)?m[ée]nages(?:\s+en\s+moyenne)?\b"
                r"(?!\s+(?:(?:en|pour|de|du|des|sur|dans)\s+(?:l[ae]\s+|les\s+|l['’]\s*)?|d['’]\s*)(?!\d{4}\b)(?!moyenne\b)"
                r"(?!(?:r[ée]gion|d[ée]partement|ville|commune|milieu)\b)[a-zéèêàâîôûç])",
                re.IGNORECASE), lambda m: "consommation moyenne par tête"),
    # #215 : « enfants scolarisés » = effectifs d'élèves scolarisés (recensement scolaire, MEN)
    (re.compile(r"\b(?:le\s+)?nombre\s+d['’]\s*enfants\s+scolaris[ée]s\b|\benfants\s+scolaris[ée]s\b", re.IGNORECASE),
     lambda m: "effectifs d'élèves scolarisés"),
]


def sans_emploi(question: str) -> str:
    """#202 : « sans emploi » rapprochait du taux d'EMPLOI (l'inverse). C'est le chômage. Puis les tournures
    exactes de la recette du 09/10 (_TOURNURES)."""
    q = _SANS_EMPLOI.sub("au chômage", question)
    for motif, par in _TOURNURES:
        q = motif.sub(par, q)
    return q


def deux_sexes(question: str) -> bool:
    """« entre hommes et femmes » : deux catégories à comparer, que la résolution ne sait pas encore servir."""
    t = texte_normalise(question)
    return bool(re.search(r"\b(femmes|filles|jigeen|djiguene)\b", t) and re.search(r"\b(hommes|garcons|goor)\b", t))


def desagregation_citee(question: str) -> dict[str, str]:
    """Désagrégation sans ambiguïté, en vocabulaire fixe (décision 0010), pour les règles locales.
    Prudente : « une femme » (ISF) n'est pas une désagrégation, « les femmes » en est une."""
    t = texte_normalise(question)
    d: dict[str, str] = {}
    # « jigéen ju nekk… » = une femme (ISF : « ñaata doom la jigéen di am »), comme « une femme » en français
    une_femme = re.search(r"\b(jigeen|djiguene) (ju|bu|bou|jou)\b|\bdoom\b", t)
    if re.search(r"\b(femmes|filles|jigeen|djiguene)\b", t) and not une_femme:
        d["sexe"] = "femmes"
    elif re.search(r"\b(hommes|garcons|goor)\b", t):
        d["sexe"] = "hommes"
    if milieu := milieu_cite(t):
        d["milieu"] = milieu
    if m := re.search(r"\b(\d{1,2})\s*(?:a|ba|-)\s*(\d{1,2})\s*ans\b", t):
        d["age"] = f"{m[1]}-{m[2]}"
    elif m := re.search(r"\bmoins de (\d{1,2}) ans\b", t):
        d["age"] = f"moins de {m[1]}"
    elif re.search(r"\b(jeunes|jeunesse)\b", t):  # « et chez les jeunes ? » : 15-24 ans, jamais perdu (#210)
        d["age"] = "15-24"
    if re.search(r"\b(elementaire|primaire)\b", t):
        d["cycle"] = "elementaire"
    elif re.search(r"\bsecondaire\b", t):
        d["cycle"] = "secondaire"
    if m := re.search(r"\b(riz|thieb|ceeb|mil|dugub|mais|sorgho)\b", t):
        d["produit"] = {"thieb": "riz", "ceeb": "riz", "dugub": "mil"}.get(m[1], m[1])
    return d


# --------------------------------------------------------------------------
# Indicateurs candidats (BM25)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Candidat:
    indicateur: Indicateur
    score: float


class Index:
    """BM25 sur les libellés FR / WO et le nom du jeu de chaque indicateur."""

    K1, B = 1.2, 0.75
    BONUS_VERIFIE = 1.5
    BONUS_NIVEAU = 1.5
    BONUS_MILIEU, MALUS_MILIEU = 1.25, 0.8

    def __init__(self, inds: dict[str, Indicateur]):
        self.inds = list(inds.values())
        self.docs = [Counter(mots(f"{x.libelle_fr} {x.libelle_wo} {nom_du_jeu(x.jeu)}")) for x in self.inds]
        self.milieux = [milieu_cite(normaliser(x.libelle_fr)) for x in self.inds]
        self._par_code = {x.code: d for x, d in zip(self.inds, self.docs, strict=True)}
        self.moyenne = sum(sum(d.values()) for d in self.docs) / max(len(self.docs), 1)
        n = len(self.docs)
        freq = Counter(m for d in self.docs for m in d)
        self.idf = {m: math.log(1 + (n - f + 0.5) / (f + 0.5)) for m, f in freq.items()}

    def mots_de(self, code: str) -> Counter:
        """Mots indexés d'un indicateur (libellés FR / WO et nom du jeu)."""
        return self._par_code.get(code, Counter())

    def requete(self, question: str) -> list[str]:
        """Mots de la question, sans les noms de zones (« Matam » ne doit pas faire remonter
        « femmes écrouées à Matam »), élargis par le vocabulaire FR / WO."""
        q = [m for m in mots(question) if not resoudre(m) and not m.isdigit()]  # ni zones ni années
        # apostrophe oubliée : « dhabitant », « lindice » (recette du 08/10)
        q = [m[1:] if m not in self.idf and len(m) > 4 and m[0] in "dl" and (m[1:] in self.idf or m[1:] in _SYN)
             else m for m in q]
        # « ñàkk » suivi d'une chose connue (« ñàkk kuraŋ », « ñàkk liggéey ») = manquer de cette chose,
        # pas la pauvreté (KBD, 06/10) : seule la chose apporte ses mots
        manque = {i for i, m in enumerate(q[:-1]) if m == "nakk" and q[i + 1] in _SYN}
        return q + [s for i, m in enumerate(q) if i not in manque for s in _SYN.get(m, ())]

    def chercher(self, question: str, k: int = 15, niveaux: set[str] | None = None) -> list[Candidat]:
        """niveaux : niveaux des zones citées (« academie »…). Un indicateur publié à ce niveau
        passe devant celui qui ne l'est pas : le même concept existe souvent dans plusieurs jeux
        (taux brut de scolarisation national dans qzvvpic, par académie dans ervtjfc)."""
        # le milieu départage sans chercher : « population rurale » n'est pas « électrification rurale » (#116)
        q = [m for m in self.requete(question) if not milieu_cite(m)]
        milieu = milieu_cite(texte_normalise(question))
        scores = []
        for x, d, m_ind in zip(self.inds, self.docs, self.milieux, strict=True):
            longueur = sum(d.values())
            s = 0.0
            for m in q:
                f = d.get(m, 0)
                if f:
                    s += self.idf[m] * f * (self.K1 + 1) / (f + self.K1 * (1 - self.B + self.B * longueur / self.moyenne))
            if s > 0:
                # les indicateurs vérifiés à la main forment le cœur servi : léger avantage
                s *= self.BONUS_VERIFIE if x.verification == "verifie" else 1
                if niveaux:
                    s *= self.BONUS_NIVEAU if niveaux <= set(x.niveaux_zone) else 1
                # « taux d'électrification » : le national passe devant le rural, à égalité de mots (#116)
                if m_ind:
                    s *= self.BONUS_MILIEU if m_ind == milieu else self.MALUS_MILIEU
                scores.append(Candidat(x, s))
        scores.sort(key=lambda c: (-c.score, c.indicateur.priorite, c.indicateur.code))
        return scores[:k]


@cache
def index() -> Index:
    return Index(indicateurs())


def aucun_mot_connu(question: str) -> bool:
    """Détermine si la question ne contient aucun mot connu (incompréhension locale)."""
    if zones_citees(question):
        return False
    if periodes_citees(question):
        return False
    if lieux_inconnus(question):
        return False
    m = mots(question)
    if not m:
        return True
    idx = index()
    for w in m:
        w_f = forme(w)
        if w in SYNONYMES or w_f in _SYN or w in idx.idf or w_f in idx.idf:
            return False
    return True

