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
}

# Amorce du lexique métier (#23) : mot de la question -> mots des libellés.
# Formes normalisées (minuscules, sans accents), FR et WO dans les deux écritures.
SYNONYMES: dict[str, tuple[str, ...]] = {
    "habitants": ("population",), "habitant": ("population",), "peuplee": ("population",),
    "nit": ("population",), "nitt": ("population",), "deuk": ("population",), "dekk": ("population",),
    "askan": ("population",), "askanu": ("population",), "jigeen": ("population", "feminin"),
    "chomeurs": ("chomage",), "liggeey": ("chomage",), "ligeey": ("chomage",), "amul": ("chomage",),
    "pauvre": ("pauvrete",), "pauvres": ("pauvrete",),
    "coute": ("prix",), "cout": ("prix",), "njeg": ("prix",), "diar": ("prix",), "jar": ("prix",),
    "ceeb": ("riz",), "thieb": ("riz",), "dugub": ("mil",),
    "inflation": ("indice", "prix", "consommation"), "ihpc": ("indice", "prix", "consommation"),
    "lekool": ("scolarisation",), "ecole": ("scolarisation",), "primaire": ("elementaire",),
    "vaccin": ("vaccines",), "vaccins": ("vaccines",), "vaccination": ("vaccines",),
    "electricite": ("eclairage", "electricite"), "courant": ("eclairage", "electricite"),
    "kouran": ("eclairage", "electricite"),
    "deces": ("mortalite",), "faatu": ("mortalite",), "mourir": ("mortalite",),
    "enfants": ("enfants",), "xale": ("enfants",), "fecondite": ("fecondite", "synthetique"),
    "inegalites": ("gini",), "pib": ("produit", "interieur", "brut"),
    "telephone": ("telephonie", "mobile"), "portable": ("telephonie", "mobile"), "telefon": ("telephonie", "mobile"),
    "touristes": ("arrivees", "residents"), "prison": ("emprisonnees",), "kaso": ("emprisonnees",),
    "prisonniers": ("emprisonnees",), "detenus": ("emprisonnees",),
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
    "njang": ("scolarisation",), "dee": ("mortalite",), "ndaw": ("population", "age"),
    "goor": ("population", "masculin"), "tej": ("emprisonnees",), "napp": ("captures", "peche"),
    "ndab": ("vehicule",), "vootuur": ("vehicule",),
    "ker": ("menages",),  # kër = ménage (KBD, 06/10)
}

_MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
         "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}


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
_VILLE = re.compile(r"\bville\s+(?:de\s+)?([A-ZÉÈÎa-zéèî][\w'’-]+)", re.IGNORECASE)
_PAS_UN_LIEU = {"sénégal", "senegal", "senegaal", "ndakaaru", "la", "le", "les", "l"}


def lieux_inconnus(question: str) -> list[str]:
    """Lieux cités mais absents du référentiel : ils ne doivent jamais devenir « le Sénégal ».
    « la ville de Thiès » n'est pas la région de Thiès : signalée aussi (réponse approchée, #12)."""
    out = [f"ville de {m[1]}" for m in _VILLE.finditer(question)]
    for m in _LIEU.finditer(question):
        nom = m[1]
        gentile = re.search(r"(ais|aise|ien|ienne|ain|aine)s?$", nom.lower())  # Sénégalais, Kaolackois…
        if nom.lower() not in _PAS_UN_LIEU and not gentile and not resoudre(nom) and not any(nom in o for o in out):
            out.append(nom)
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


def periodes_citees(question: str) -> list[str]:
    """« mars 2025 » -> 2025-03 ; « 2023 » -> 2023 ; « T2 2024 » -> 2024-T2. Dans l'ordre."""
    t = texte_normalise(question)
    out = []
    for m in re.finditer(r"\b(?:(?P<mois>" + "|".join(_MOIS) + r")\s+)?(?:(?P<t>t[1-4])\s+)?"
                         r"(?P<an>(?:19|20)\d\d)\b", t):
        if m["mois"]:
            out.append(f"{m['an']}-{_MOIS[m['mois']]:02d}")
        elif m["t"]:
            out.append(f"{m['an']}-T{m['t'][1]}")
        else:
            out.append(m["an"])
    return out


def desagregation_citee(question: str) -> dict[str, str]:
    """Désagrégation sans ambiguïté, en vocabulaire fixe (décision 0010), pour les règles locales.
    Prudente : « une femme » (ISF) n'est pas une désagrégation, « les femmes » en est une."""
    t = texte_normalise(question)
    d: dict[str, str] = {}
    if re.search(r"\b(femmes|filles|jigeen|djiguene)\b", t):
        d["sexe"] = "femmes"
    elif re.search(r"\b(hommes|garcons|goor)\b", t):
        d["sexe"] = "hommes"
    if re.search(r"\b(ruraux|rurales?|rural|goxaan)\b", t):  # « gox-goxaan yi » = le milieu rural (KBD)
        d["milieu"] = "rural"
    elif re.search(r"\b(urbains?|urbaines?)\b", t):
        d["milieu"] = "urbain"
    if m := re.search(r"\b(\d{1,2})\s*(?:a|ba|-)\s*(\d{1,2})\s*ans\b", t):
        d["age"] = f"{m[1]}-{m[2]}"
    elif m := re.search(r"\bmoins de (\d{1,2}) ans\b", t):
        d["age"] = f"moins de {m[1]}"
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

    def __init__(self, inds: dict[str, Indicateur]):
        self.inds = list(inds.values())
        self.docs = [Counter(mots(f"{x.libelle_fr} {x.libelle_wo} {nom_du_jeu(x.jeu)}")) for x in self.inds]
        self.moyenne = sum(sum(d.values()) for d in self.docs) / max(len(self.docs), 1)
        n = len(self.docs)
        freq = Counter(m for d in self.docs for m in d)
        self.idf = {m: math.log(1 + (n - f + 0.5) / (f + 0.5)) for m, f in freq.items()}

    def requete(self, question: str) -> list[str]:
        """Mots de la question, sans les noms de zones (« Matam » ne doit pas faire remonter
        « femmes écrouées à Matam »), élargis par le vocabulaire FR / WO."""
        q = [m for m in mots(question) if not resoudre(m) and not m.isdigit()]  # ni zones ni années
        # « ñàkk » suivi d'une chose connue (« ñàkk kuraŋ », « ñàkk liggéey ») = manquer de cette chose,
        # pas la pauvreté (KBD, 06/10) : seule la chose apporte ses mots
        manque = {i for i, m in enumerate(q[:-1]) if m == "nakk" and q[i + 1] in _SYN}
        return q + [s for i, m in enumerate(q) if i not in manque for s in _SYN.get(m, ())]

    def chercher(self, question: str, k: int = 15, niveaux: set[str] | None = None) -> list[Candidat]:
        """niveaux : niveaux des zones citées (« academie »…). Un indicateur publié à ce niveau
        passe devant celui qui ne l'est pas : le même concept existe souvent dans plusieurs jeux
        (taux brut de scolarisation national dans qzvvpic, par académie dans ervtjfc)."""
        q = self.requete(question)
        scores = []
        for x, d in zip(self.inds, self.docs, strict=True):
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

