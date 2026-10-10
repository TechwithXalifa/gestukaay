"""Autocomplétion de la question (EF-10, prévue en V1.1).

Pendant que l'usager tape, le site propose des questions qui marchent : moins de refus, moins de
reformulations. Rien n'est inventé ni calculé ici, et aucune donnée du socle n'est touchée :
  - des questions types, vérifiées sur le moteur réel (réponse exacte le 10/10), dont la zone suit
    celle que l'usager a commencé à écrire ;
  - les indicateurs du catalogue (vérifiés d'abord) dont le libellé contient les mots tapés, publiés au
    niveau de la zone demandée.
Les questions des autres usagers ne sont jamais proposées : elles peuvent contenir des données
personnelles (confidentialité).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

from gestukaay_socle.zones import normaliser, zones
from pydantic import BaseModel

LIMITE = 6
LONGUEUR_MIN = 2
# Mots outils retirés avant de chercher dans le catalogue (tous les mots doivent y figurer)
VIDES = frozenset(
    ["a", "au", "aux", "avec", "ce", "combien", "comment", "d", "de", "des", "du", "en", "est", "et", "l", "la", "le", "les", "leur", "mon", "ou", "par", "pour", "quel", "quelle", "quelles", "quels", "qu", "que", "qui", "sa", "se", "ses", "son", "sur", "un", "une", "y", "dans"]
)


class IndicateurSuggere(BaseModel):
    code: str
    libelle: str


class Suggestion(BaseModel):
    texte: str
    indicateur: IndicateurSuggere | None = None


class SuggestionsResponse(BaseModel):
    suggestions: list[Suggestion]


@dataclass(frozen=True)
class QuestionType:
    gabarit: str  # {zone} : « à Kolda », « au Sénégal »
    mots: tuple[str, ...]  # mots-clés normalisés ; un mot tapé doit commencer l'un d'eux
    code: str  # l'indicateur servi (le catalogue ne le propose pas une seconde fois)
    defaut: str = "au Sénégal"  # sans zone tapée
    niveaux: tuple[str, ...] = ("pays", "region")


# Questions vérifiées sur le moteur réel (réponse exacte le 10/10) : la formulation est celle qui marche.
QUESTIONS_TYPES = (
    QuestionType("Combien d'habitants {zone} ?", ("habitants", "population", "nombre", "gens", "personnes", "vivent"),
                 "pvswjnd", niveaux=("pays", "region", "departement")),
    QuestionType("Quel est le taux de pauvreté {zone} ?", ("pauvrete", "pauvres", "taux"), "jcvcajc.taux-de-pauvrete"),
    QuestionType("Quel est le taux de chômage {zone} ?", ("chomage", "chomeurs", "emploi", "travail", "taux"), "dwibrlf"),
    QuestionType("Combien coûte le kilo de riz brisé {zone} ?", ("riz", "prix", "kilo", "coute", "brise"),
                 "feujxob.riz-brise-ordinaire-au-detail", defaut="au détail", niveaux=("region",)),
    QuestionType("Quel est le taux de scolarisation {zone} ?", ("scolarisation", "ecole", "eleves", "taux"),
                 "ervtjfc.taux-brut-de-scolarisation"),
    QuestionType("Quel est le taux d'urbanisation {zone} ?", ("urbanisation", "villes", "urbain", "taux"),
                 "rfegvpb.taux-durbanisation"),
    QuestionType("Quel est le taux d'électrification {zone} ?", ("electrification", "electricite", "courant", "taux"),
                 "vlaobkb"),
    QuestionType("Quelle proportion des enfants sont complètement vaccinés {zone} ?",
                 ("vaccination", "vaccines", "vaccin", "enfants", "sante"), "wdvdnub.proportion-denfants-de-12-a-23-mois"),
    QuestionType("Quel est l'indice de Gini {zone} ?", ("gini", "inegalites", "indice"), "qjyrtof.gini"),
    QuestionType("Quelle est la part des ménages avec un robinet dans le logement ?", ("robinet", "eau", "menages"),
                 "kdtstle.robinet-dans-logement-concession", defaut="", niveaux=("pays",)),
    QuestionType("Quel est l'indice des prix à la consommation ?", ("inflation", "prix", "indice", "consommation", "ihpc"),
                 "tsghpfc.indice-global", defaut="", niveaux=("pays",)),
    QuestionType("Quel est le PIB du Sénégal ?", ("pib", "croissance", "economie", "richesse", "produit"),
                 "rgohtcc", defaut="", niveaux=("pays",)),
)


@dataclass(frozen=True)
class _Zone:
    code: str
    niveau: str
    libelle: str
    nom: str  # normalisé


@cache
def _zones() -> tuple[_Zone, ...]:
    """Pays, régions et départements (jamais les académies : niveau à part, 0003), régions d'abord."""
    ordre = {"pays": 0, "region": 1, "departement": 2}
    vues: dict[str, _Zone] = {}
    for z in sorted(zones().values(), key=lambda z: ordre.get(z.niveau, 9)):
        if z.niveau not in ordre:
            continue
        for nom in (z.libelle_fr, *z.variantes):
            vues.setdefault(normaliser(nom), _Zone(z.code, z.niveau, z.libelle_fr, normaliser(nom)))
    return tuple(vues.values())


def _dans(zone: _Zone) -> str:
    return "au Sénégal" if zone.code == "SN" else f"à {zone.libelle}"


def _trouver_zone(mots: list[str]) -> tuple[_Zone | None, list[str]]:
    """La zone écrite dans la question (un à trois mots, le dernier pouvant être commencé) et les mots restants."""
    for taille in (3, 2, 1):
        for i in range(len(mots) - taille + 1):
            nom = " ".join(mots[i:i + taille])
            exacte = next((z for z in _zones() if z.nom == nom), None)
            # « kol » au bout de la question : Kolda (la première zone qui commence ainsi, régions d'abord)
            # Deux lettres suffisent après d'autres mots (« chômage th ») ; seules, elles restent un début de mot
            minimum = 2 if i > 0 else 3
            commencee = None
            if i + taille == len(mots) and len(nom) >= minimum and nom not in VIDES:  # « ou » n'est pas Oussouye
                commencee = next((z for z in _zones() if z.nom.startswith(nom)), None)
            if z := exacte or commencee:
                return z, mots[:i] + mots[i + taille:]
    return None, mots


def _correspond(mots: list[str], cles: tuple[str, ...]) -> bool:
    return bool(mots) and all(any(c.startswith(m) for c in cles) for m in mots)


# Élision détachée avant de normaliser (qui colle les apostrophes : M'bour = Mbour) : « d'habitants » -> « d habitants »
_ELISION = re.compile(r"\b([cdjlnst]|qu)['’](?=\w)", re.IGNORECASE)


def suggerer(moteur, texte: str, limite: int = LIMITE) -> list[Suggestion]:
    norm = normaliser(_ELISION.sub(r"\1 ", texte))
    if len(norm) < LONGUEUR_MIN:
        return []
    zone, mots = _trouver_zone(norm.split())
    utiles = [m for m in mots if m not in VIDES and len(m) >= 2]
    sorties: list[Suggestion] = []

    def ajouter(s: Suggestion) -> None:
        if len(sorties) < limite and all(normaliser(x.texte) != normaliser(s.texte) for x in sorties):
            sorties.append(s)

    # Seulement une zone (« kolda ») : les questions types qui se posent sur elle
    types = [qt for qt in QUESTIONS_TYPES if _correspond(utiles, qt.mots)] if utiles else \
        [qt for qt in QUESTIONS_TYPES if "{zone}" in qt.gabarit] if zone else []
    servis: set[str] = set()
    for qt in types:
        if zone and zone.niveau not in qt.niveaux:
            continue
        lieu = _dans(zone) if zone else qt.defaut
        ajouter(Suggestion(texte=re.sub(r"\s+", " ", qt.gabarit.format(zone=lieu)).strip()))
        servis.add(qt.code)

    if utiles:
        lieu = f" {_dans(zone)}" if zone else ""
        for ind in _indicateurs(moteur, utiles, zone.niveau if zone else None):
            if ind.code not in servis:
                ajouter(Suggestion(texte=f"{ind.libelle}{lieu}",
                                   indicateur=IndicateurSuggere(code=ind.code, libelle=ind.libelle)))
    return sorties


LIBELLE_MAX = 70  # au-delà, un libellé du portail (« 280 electricite, gaz et eau — Consommation… ») ne se lit plus


def _indicateurs(moteur, mots: list[str], niveau: str | None) -> list:
    """Les indicateurs dont le LIBELLÉ contient chaque mot (le catalogue cherche aussi dans l'opération et le
    producteur : « population » y trouvait les détenus). Vérifiés d'abord ; un non vérifié seulement s'il a un
    libellé court et lisible (sans « — jeu de données », sans chiffre ni symbole en tête)."""
    cat = moteur.catalogue(None, " ".join(mots), niveau, 100, 0)
    garder = [i for i in cat.indicateurs if all(m in normaliser(i.libelle) for m in mots)]
    verifies = [i for i in garder if i.verifie]
    lisibles = [i for i in garder if not i.verifie and len(i.libelle) <= LIBELLE_MAX
                and " — " not in i.libelle and i.libelle[:1].isalpha()]
    return verifies + sorted(lisibles, key=lambda i: len(i.libelle))
