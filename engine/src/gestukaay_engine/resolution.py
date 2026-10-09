"""Résolution exacte : requête structurée -> valeurs officielles sourcées (issue #11, décision 0011).

Sans LLM, entièrement déterministe. Aucun recalcul : chaque valeur rendue est
une ligne du socle extrait, avec son observation_id.

Valeurs par défaut (cahier, US-06) :
  - sans zone : le national ; si le jeu n'a qu'une zone (prix relevés à Dakar), celle-là ;
  - sans période : la dernière publiée (signalée dans `Resolution.defauts`) ;
  - sans désagrégation : le total de chaque dimension (« Total », « TOTALE », « Ensemble »…).

Strict : si la zone, la période ou la désagrégation demandées n'existent pas, ou
si une dimension n'a pas de total et que la question ne dit rien, la résolution
rend `Introuvable` avec la raison et ce qui est disponible. Les propositions
(zone parente, période voisine, « pour quel produit ? ») relèvent de #12.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from functools import cache
from typing import Literal

from gestukaay_contracts.models import (
    Graphique,
    PeriodeResolue,
    RefIndicateur,
    RefZone,
    RequeteStructuree,
    Resultat,
    Source,
)
from gestukaay_socle.indicateurs import REFERENTIELS, Indicateur, indicateurs
from gestukaay_socle.zones import normaliser, zones

from .candidats import (
    ORDRE_ASC,
    est_evolution,
    extremum,
    fenetre_annees,
    fenetre_periodes,
    periodes_citees,
    texte_normalise,
    zones_citees,
)
from .gabarits import formater
from .graphique import (
    graphique_classement,
    graphique_comparaison_zones,
    graphique_contexte_valeur,
    graphique_evolution,
)
from .socle import Observation, Socle

Raison = Literal["indicateur_inconnu", "zone_non_couverte", "periode_absente", "desagregation_absente",
                 "desagregation_ambigue", "non_traite"]

# Au-delà, une valeur publiée est une prévision (refus, #116). L'année du jour au démarrage, et non plus 2026 écrit
# en dur (audit du 09/10) : en 2027, « l'année dernière » aurait donné 2025 et une question sur 2027 une prévision
ANNEE_EN_COURS = datetime.now(UTC).year

_TOTAUX = {"total", "totale", "totaux", "ensemble", "global", "globale", "tous", "toutes", "all",
           "les deux sexes", "deux sexes", "ensemble du pays", "national"}

# Vocabulaire fixe de la compréhension (décision 0010) -> dimension du jeu, puis modalité
_CLES = {
    "sexe": re.compile(r"^(sexe|sex|genre)$"),
    "milieu": re.compile(r"milieu"),
    "age": re.compile(r"(^| )(age|ages)( |$)"),
    "cycle": re.compile(r"cycle|niveau d enseignement"),
    "produit": re.compile(r"produit|culture|cereale|denree|speculation"),
}
_VALEURS = {
    "femmes": {"feminin", "femme", "femmes", "f", "fille", "filles", "women", "female"},
    "hommes": {"masculin", "homme", "hommes", "m", "garcon", "garcons", "men", "male"},
    "urbain": {"urbain", "urbaine", "urban"},
    "rural": {"rural", "rurale"},
    "elementaire": {"elementaire", "primaire"},
}
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
         "novembre", "décembre"]


@dataclass
class Resolution:
    resultats: list[Resultat]
    defauts: dict[str, bool] = field(default_factory=dict)  # {"zone": …, "periode": …} pris par défaut
    graphique: Graphique | None = None


@dataclass
class Introuvable:
    raison: Raison
    detail: str
    disponibles: list[str] = field(default_factory=list)  # zones ou périodes publiées
    choix: dict[str, list[str]] = field(default_factory=dict)  # dimension ambiguë -> modalités
    dimension_absente: str | None = None  # clé canonique (« sexe ») que ce jeu ne publie pas du tout


# --------------------------------------------------------------------------
# Désagrégation
# --------------------------------------------------------------------------

def est_total(modalite: str) -> bool:
    return normaliser(modalite) in _TOTAUX


def _nombres(texte: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", texte)]


_JEUNES = {"jeunes", "jeune", "jeunesse", "les jeunes"}


def correspond(canonique: str, valeur: str, modalite: str) -> bool:
    """La modalité du jeu correspond-elle à la valeur canonique (« femmes » ~ « Féminin ») ?"""
    m, v = normaliser(modalite), normaliser(valeur)
    if v == "total":
        return m in _TOTAUX
    for groupe in _VALEURS.values():  # « primaire » ~ « Elémentaire », « filles » ~ « Féminin »
        if v in groupe:
            return m in groupe or bool(set(m.split()) & groupe)
    if canonique == "age":
        v = "15-24" if v in _JEUNES else v  # « les jeunes » : la tranche 15-24 ans (recette du 09/10, #210)
        return m == v or (_nombres(v) and _nombres(v) == _nombres(m)) or (v in m)
    return v == m or v in m.split()


def dimension(canonique: str, dims: set[str]) -> str | None:
    for d in sorted(dims):
        if _CLES[canonique].search(normaliser(d)):
            return d
    return None


@cache
def defauts_desagregation() -> dict[str, dict[str, str]]:
    """Jeu -> {dimension: modalité} quand une dimension n'a pas de total (PIB : base, prix, approche)."""
    out: dict[str, dict[str, str]] = {}
    with (REFERENTIELS / "defauts_desagregation.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            out.setdefault(r["dataset_id"], {})[r["dimension"]] = r["modalite"]
    return out


# Une modalité dite en wolof (formes de KBD) : « nappkat yu ndaw yi » = les petits pêcheurs (WO-009, 08/10)
# « yàpp géej » = les poissons (WO-009, son équivalent français dit « poisson »)
_MODALITES_WO = {"peche artisanale": ("nappkat yu ndaw",), "poisson": ("yapp geej",)}


def _sing(texte: str) -> str:
    """Pluriel simple retiré, mot à mot : « POISSONS » est cité par « tonnes de poisson »."""
    return " ".join(m[:-1] if len(m) > 3 and m.endswith("s") else m for m in texte.split())


def citee(modalite: str, question: str) -> bool:
    """La modalité est-elle nommée dans la question (« Pêche artisanale », « Français ») ?"""
    m, q = normaliser(modalite).split(), f" {_sing(normaliser(question))} "
    nom = _sing(" ".join(m))
    return bool(m) and len("".join(m)) >= 3 and (f" {nom} " in q or any(f" {f} " in q for f in _MODALITES_WO.get(nom, ())))


def imposer(lignes: list[Observation], demande: dict[str, str]) -> tuple[list[Observation], Introuvable | None]:
    """Applique ce que la question demande (vocabulaire fixe), toutes périodes confondues."""
    dims = {k for o in lignes for k, _ in o.desagregation}
    imposees: dict[str, str] = {}
    for canon, valeur in demande.items():
        d = dimension(canon, dims) if canon in _CLES else None
        if d is None:
            if normaliser(valeur) == "total":
                continue  # demander le total, c'est le défaut
            # la clé ne colle à aucune dimension (« produit = français ») : la modalité existe-t-elle ailleurs ?
            ailleurs = [(k, m) for k in sorted(dims) for m in sorted({o.dims().get(k) for o in lignes} - {None})
                        if not est_total(m) and correspond(canon, valeur, m)]
            if len(ailleurs) != 1:
                return [], Introuvable("desagregation_absente", f"{canon} = {valeur} : non publié pour cet indicateur",
                                       dimension_absente=canon)
            d = ailleurs[0][0]
        modalites = sorted({o.dims().get(d) for o in lignes} - {None})
        trouvees = [m for m in modalites if correspond(canon, valeur, m)]
        if not trouvees:
            return [], Introuvable("desagregation_absente", f"{canon} = {valeur}", choix={d: modalites})
        imposees[d] = trouvees[0]
    return [o for o in lignes if all(o.dims().get(d) == v for d, v in imposees.items())], None


def completer(lignes: list[Observation], question: str = "",
              defauts: dict[str, str] | None = None) -> tuple[list[Observation], Introuvable | None]:
    """Fixe les dimensions restantes, dans l'ordre : nommée dans la question, unique, total, défaut
    déclaré du jeu ; sinon ambiguë (les modalités sont rendues pour proposer un choix)."""
    defauts = defauts or {}
    dims = {k for o in lignes for k, _ in o.desagregation}
    imposees: dict[str, str] = {}
    ambigues: dict[str, list[str]] = {}
    for d in sorted(dims):
        modalites = sorted({o.dims().get(d) for o in lignes} - {None})
        nommees = [m for m in modalites if not est_total(m) and citee(m, question)]
        totaux = [m for m in modalites if est_total(m)]
        if len(modalites) == 1:
            imposees[d] = modalites[0]
        elif len(nommees) == 1:
            imposees[d] = nommees[0]
        elif totaux:
            imposees[d] = totaux[0]
        elif defauts.get(d) in modalites:
            imposees[d] = defauts[d]
        else:
            ambigues[d] = modalites
    if ambigues:
        return [], Introuvable("desagregation_ambigue", "préciser : " + ", ".join(ambigues), choix=ambigues)
    return [o for o in lignes if all(o.dims().get(d, v) == v for d, v in imposees.items())], None


def choisir(lignes: list[Observation], demande: dict[str, str], question: str = "",
            defauts: dict[str, str] | None = None) -> tuple[list[Observation], Introuvable | None]:
    """imposer() puis completer(), sur des lignes d'une même période."""
    lignes, erreur = imposer(lignes, demande)
    return ([], erreur) if erreur else completer(lignes, question, defauts)


# --------------------------------------------------------------------------
# Libellés et formatage (provisoires : les gabarits #16 les affineront)
# --------------------------------------------------------------------------

def libelle_periode(p: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}", p):
        return f"{_MOIS[int(p[5:7]) - 1]} {p[:4]}"
    if re.fullmatch(r"\d{4}-T[1-4]", p):
        return f"{p[-1]}{'er' if p[-1] == '1' else 'e'} trimestre {p[:4]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p):
        return f"{int(p[8:])} {_MOIS[int(p[5:7]) - 1]} {p[:4]}"
    return p


def _date_fr(d: date) -> str:
    return f"{'1er' if d.day == 1 else d.day} {_MOIS[d.month - 1]} {d.year}"


@cache
def _operations() -> dict[str, str]:
    """Opération (ENES, EHCVM…) des fiches de jeux (#7), si elles sont présentes."""
    f = REFERENTIELS / "jeux.csv"
    if not f.exists():
        return {}
    with f.open(encoding="utf-8") as fh:
        return {r["dataset_id"]: r.get("operation", "") for r in csv.DictReader(fh, delimiter=";")}


@cache
def _sources_citees() -> dict[str, tuple[str, str]]:
    """Producteur et opération à citer, déclarés avec leur preuve (sources_citees.csv, #16)."""
    f = REFERENTIELS / "sources_citees.csv"
    if not f.exists():
        return {}
    with f.open(encoding="utf-8") as fh:
        return {r["dataset_id"]: (r["producteur"], r["operation"]) for r in csv.DictReader(fh, delimiter=";")}


def producteur_et_operation(dataset_id: str, s, ind: Indicateur) -> tuple[str, str]:
    """Déclarés si possible ; sinon le producteur du portail lisible et l'opération du portail
    si elle est courte, ou le titre du jeu (EF-35 : « ANSD, RGPH-5 (2023) »)."""
    if dataset_id in _sources_citees():
        return _sources_citees()[dataset_id]
    producteur = (s.producteur if s else "") or ind.producteur
    producteur = producteur.replace("-", " ") if "-" in producteur and " " not in producteur else producteur
    operation = _operations().get(dataset_id, "")
    if not operation or len(operation) > 60:
        from gestukaay_socle.indicateurs import nom_du_jeu
        operation = nom_du_jeu(s.titre if s else ind.jeu)
    return producteur, operation


def source(socle: Socle, o: Observation, ind: Indicateur) -> Source:
    s = socle.sources.get(o.source_id)
    publie = (s.date_publication if s and s.date_publication else None) or date(1970, 1, 1)
    producteur, operation = producteur_et_operation(o.source_id, s, ind)
    licence = s.licence if s else ""
    libelle = " · ".join(x for x in (producteur, operation, f"publié le {_date_fr(publie)}", licence) if x)
    return Source(producteur=producteur, operation=operation, titre=(s.titre if s else ind.jeu),
                  date_publication=publie, licence=licence, url=s.url if s else "", libelle=libelle)


def ref_zone(code: str) -> RefZone:
    z = zones()[code]
    libelle = f"académie de {z.libelle_fr}" if z.niveau == "academie" and not normaliser(
        z.libelle_fr).startswith(("academie", "ia ")) else z.libelle_fr
    return RefZone(code=code, libelle=libelle, niveau=z.niveau)


def resultat(socle: Socle, o: Observation, ind: Indicateur, langue: str = "fr",
             sans_choix: frozenset[str] = frozenset()) -> Resultat:
    """sans_choix : dimensions à une seule modalité (« catégorie : Indices de pauvreté ») : elles ne
    précisent rien, on ne les affiche pas."""
    desag = {k: v for k, v in o.desagregation if not est_total(v) and k not in sans_choix}
    libelle = (ind.libelle_wo if langue == "wo" and ind.libelle_wo else ind.libelle_fr)
    unite = ind.unite_affichee or ind.unite or o.unite
    return Resultat(
        indicateur=RefIndicateur(code=ind.code, libelle=libelle), zone=ref_zone(o.zone),
        periode=PeriodeResolue(valeur=o.periode, libelle=libelle_periode(o.periode)),
        desagregation=desag or None, valeur=o.valeur, valeur_affichee=formater(o.valeur, unite)[0],
        unite=unite, source=source(socle, o, ind),
        observation_id=o.id, nature=o.nature if o.nature in ("observee", "estimation", "projection") else None,
        base_projection=o.base_projection or None,
    )


# --------------------------------------------------------------------------
# Résolution
# --------------------------------------------------------------------------

def portee_par_indicateur(ind: Indicateur, valeur: str) -> bool:
    """« riz » pour « Prix du riz brisé », « moins de 5 » pour « … enfants de moins de 5 ans » :
    la précision est déjà dans l'indicateur, ce n'est pas une dimension à chercher."""
    texte = f" {normaliser(f'{ind.libelle_fr} {ind.valeur_portail} {ind.jeu}')} "
    # « urbain » pour « Taux d'urbanisation » : la part urbaine, par définition (« ñoo dëkk ci dëkk yi », KBD 08/10)
    if normaliser(valeur) == "urbain" and "urbanisation " in texte:  # « d'urbanisation » -> « durbanisation »
        return True
    # « rural » pour « Taux d'électrification rurale » (#116) : accord en genre et en nombre
    return all(re.search(rf" {re.escape(m)}(e|s|es)? ", texte) for m in normaliser(valeur).split())


def periode_par_defaut(lignes: list[Observation]) -> tuple[str, bool]:
    """Période servie quand la question n'en cite pas (#116, 0035), et si c'est la « dernière donnée publiée ».
    La dernière période jusqu'à l'année en cours, quelle que soit sa nature (l'ISF 2025 des projections
    2023-2073, badge projection) ; jamais une année future : « l'espérance de vie » donne 2026, pas 2035.
    Une série qui ne commence qu'après l'année en cours donne sa première période."""
    periodes = sorted({o.periode for o in lignes})
    passees = [p for p in periodes if p[:4] <= str(ANNEE_EN_COURS)]
    p = passees[-1] if passees else periodes[0]
    # « dernière donnée publiée » : la fin de la série, ou une valeur observée suivie seulement de projections
    return p, p == periodes[-1] or any(o.nature == "observee" for o in lignes if o.periode == p)


def academie_equivalente(zone: str, publiees: list[str]) -> str | None:
    """Une région servie par une seule académie qui la recouvre exactement (`couvre` = la région : Sédhiou,
    Kolda…) : même territoire, la valeur de l'académie est servie, sous son nom. Pas Dakar (trois académies)."""
    equiv = [z.code for z in zones().values() if z.niveau == "academie" and z.couvre == (zone,)]
    return equiv[0] if len(equiv) == 1 and equiv[0] in publiees else None


def zone_de_la_serie(socle: Socle, code: str, zone: str | None) -> str | None:
    """La zone demandée, sinon celle que resoudre_un prendra : le Sénégal, ou la seule zone publiée (riz : Dakar)."""
    if zone:
        return zone
    publiees = {o.zone for o in socle.observations(code)}
    return "SN" if "SN" in publiees else next(iter(publiees)) if len(publiees) == 1 else None


def resoudre_un(socle: Socle, ind: Indicateur, zone: str | None, periode: str | None,
                demande: dict[str, str], langue: str = "fr",
                question: str = "", annee: str = "fin") -> tuple[Resultat, dict] | Introuvable:
    """Une valeur : indicateur × zone × période × désagrégation.
    annee : pour une année demandée sur une série mensuelle ou trimestrielle (« le riz en 2019 »), le dernier
    mois de l'année (« fin ») ou le premier (« debut », pour « depuis 2020 ») ; le mois est dit dans la réponse.
    « choix » (valeur simple) : aucun mois n'est servi, les derniers de l'année sont proposés (approchée)."""
    lignes = socle.observations(ind.code)
    if not lignes:
        return Introuvable("indicateur_inconnu", f"{ind.code} : aucune valeur dans le socle")
    publiees = sorted({o.zone for o in lignes})
    defauts = {"zone": zone is None, "periode": periode is None}
    if zone is None:
        zone = "SN" if "SN" in publiees else publiees[0] if len(publiees) == 1 else None
        if zone is None:
            return Introuvable("zone_non_couverte", "pas de valeur nationale", disponibles=publiees)
    if zone not in publiees:
        zone = academie_equivalente(zone, publiees) or zone
    if zone not in publiees:
        return Introuvable("zone_non_couverte", f"{zone} non publié", disponibles=publiees)
    demande = {k: v for k, v in demande.items() if not portee_par_indicateur(ind, v)}
    # 1. ce que la question demande (riz : seule année publiée à Kaolack, 2016) ;
    # 2. la période ; 3. les autres dimensions, ambiguës seulement si plusieurs modalités existent cette année-là
    lignes, erreur = imposer([o for o in lignes if o.zone == zone], demande)
    if erreur:
        return erreur
    periodes = sorted({o.periode for o in lignes})
    p = periode
    if p is None:
        p, defauts["periode"] = periode_par_defaut(lignes)
    if p not in periodes and re.fullmatch(r"\d{4}", p or "") and (dans := [x for x in periodes if x.startswith(p + "-")]):
        if annee == "choix":  # valeur simple : le mois est proposé, pas choisi à la place de l'utilisateur (KBD, 08/10)
            return Introuvable("periode_absente", f"{p} publié par mois ou par trimestre", disponibles=dans)
        p = dans[0] if annee == "debut" else dans[-1]  # recette du 08/10 : « n'existe pas » pour le riz en 2019
    if p not in periodes:
        return Introuvable("periode_absente", f"{p} non publié", disponibles=periodes)
    retenues, erreur = completer([o for o in lignes if o.periode == p], question,
                                 defauts_desagregation().get(ind.dataset_id))
    if erreur:
        return erreur
    if not retenues:  # modalités retenues une à une sans ligne commune (410 questions du 08/10 : IndexError)
        return Introuvable("desagregation_ambigue", "aucune ligne pour cette combinaison de modalités")
    if len({o.desagregation for o in retenues}) > 1:  # ne devrait pas arriver après choisir()
        return Introuvable("desagregation_ambigue", "plusieurs lignes pour la même clé")
    toutes = socle.observations(ind.code)
    uniques = frozenset(k for k in {k for o in toutes for k, _ in o.desagregation}
                        if len({o.dims().get(k) for o in toutes} - {None}) == 1)
    return resultat(socle, retenues[0], ind, langue, uniques), defauts


def periode_par_zone(zones_cibles: list[str], question: str) -> dict[str, str] | None:
    """« Le taux de pauvreté de Dakar en 2011 et celui de Thiès en 2022 » : chaque zone a son année (recette du
    09/10, #212 : Thiès était servie en 2011 sans le dire). Seulement si la question se coupe en deux morceaux,
    chacun avec une zone et une année ; sinon None (une seule période pour toutes les zones)."""
    if len(zones_cibles) != 2:
        return None
    mots_ = question.split()
    for k in range(1, len(mots_)):
        avant, apres = " ".join(mots_[:k]), " ".join(mots_[k:])
        if zones_citees(avant) == zones_cibles[:1] and zones_citees(apres) == zones_cibles[1:]:
            p1, p2 = periodes_citees(avant), periodes_citees(apres)
            if len(p1) == 1 and len(p2) == 1 and p1 != p2:
                return {zones_cibles[0]: p1[0], zones_cibles[1]: p2[0]}
    return None


def meme_categorie(socle: Socle, ind: Indicateur, resultats: list[Resultat]) -> Introuvable | None:
    """Un classement ou une comparaison de zones compare la même catégorie partout. Chaque zone fixe ses
    dimensions seule (une catégorie unique y est prise d'office) : benchmark LLM du 09/10, WO-009, la pêche
    artisanale de la côte et la pêche continentale de Matam dans le même graphique. Sinon : le choix."""
    par_id = {o.id: o for o in socle.observations(ind.code)}
    dims = [{k: "total" if est_total(v) else v for k, v in par_id[r.observation_id].desagregation} for r in resultats]
    differentes = {k for d in dims for k in d if len({x.get(k, "total") for x in dims}) > 1}  # absente = total
    # d'abord la dimension où les zones ont deux catégories réelles (artisanale / continentale), pas un total
    differentes = sorted(differentes, key=lambda k: (sum(x.get(k, "total") == "total" for x in dims), k))
    if not differentes:
        return None
    choix = {k: sorted({m for o in par_id.values() if (m := o.dims().get(k)) and not est_total(m)}) for k in differentes}
    return Introuvable("desagregation_ambigue", "catégorie différente selon la zone : " + ", ".join(differentes),
                       choix=choix)


def _chercher_indicateur(code: str | None) -> Indicateur | None:
    if not code:
        return None
    ind = indicateurs().get(code)
    if ind is None and "." not in code:
        ind = next((i for i in indicateurs().values() if i.code.startswith(code + ".")), None)
    return ind




def ordre_effectif(requete: RequeteStructuree, question: str = "") -> str:
    """Sens du classement : requete.ordre, sinon repli lexical (« le moins », « le plus faible »).
    Partagé par le tri (ici) et la phrase (gabarits), pour qu'ils ne se contredisent jamais."""
    if requete.ordre == "desc" and ORDRE_ASC.search(texte_normalise(question)):
        return "asc"
    return requete.ordre


def resoudre(socle: Socle, requete: RequeteStructuree, langue: str = "fr", question: str = "",
             lieux_inconnus: list[str] | None = None) -> Resolution | Introuvable:
    """Intentions « valeur », « comparaison » et « classement » (issue #14).
    lieux_inconnus : lieux cités mais absents du référentiel (« Touba », « la ville de Thiès ») :
    jamais remplacés par le national."""
    if lieux_inconnus:
        return Introuvable("zone_non_couverte", "lieu hors référentiel : " + ", ".join(lieux_inconnus))
    if requete.intention == "hors_perimetre" or not requete.indicateur:
        return Introuvable("indicateur_inconnu", "hors périmètre")

    ind = _chercher_indicateur(requete.indicateur)
    if ind is None:
        return Introuvable("indicateur_inconnu", f"{requete.indicateur} : code inconnu du référentiel")

    demande = dict(requete.desagregation or {})

    # -----------------------------------------------------------------------
    # Période du plus haut / plus bas niveau d'une série (recette du 08/10) : chaque période est résolue comme
    # une valeur ; on garde la plus haute ou la plus basse. Aucun calcul, une valeur publiée.
    # -----------------------------------------------------------------------
    if (sens := extremum(question)) and len(requete.zones or []) <= 1:
        z = requete.zones[0] if requete.zones else None
        citees = periodes_citees(question)
        debut = requete.periode.valeur if requete.periode.type != "derniere" else (citees[0] if citees else None)
        fin_ = requete.periode.fin or (citees[1] if len(citees) > 1 else None)
        ouvert = bool(re.search(r"\b(depuis|apres)\b", normaliser(question)))
        serie = sorted({o.periode for o in socle.observations(ind.code) if o.zone == zone_de_la_serie(socle, ind.code, z)})
        serie = [x for x in serie if x[:4] <= str(ANNEE_EN_COURS)
                 and (not debut or x[:len(debut)] >= debut) and (not fin_ or x[:len(fin_)] <= fin_)
                 and (not debut or fin_ or ouvert or x.startswith(debut))]  # « en 2018 » : l'année seule
        trouves = [r for x in serie if not isinstance(r := resoudre_un(socle, ind, z, x, demande, langue, question),
                                                       Introuvable) and r[0].periode.valeur == x]
        if len(trouves) >= 2:
            choisi = (min if sens == "min" else max)(trouves, key=lambda r: r[0].valeur)
            choisi[0].mise_en_evidence = True
            return Resolution([choisi[0]], {**choisi[1], "extremum": sens, "debut": trouves[0][0].periode.libelle,
                                             "fin": trouves[-1][0].periode.libelle}, None)

    # -----------------------------------------------------------------------
    # Classement (#14) : 14 régions ou 16 académies
    # -----------------------------------------------------------------------
    if requete.intention == "classement":
        periode = None if requete.periode.type == "derniere" else requete.periode.valeur
        lignes = socle.observations(ind.code)
        if not lignes:
            return Introuvable("indicateur_inconnu", f"{ind.code} : aucune valeur dans le socle")
        publiees = {o.zone for o in lignes}

        if requete.zones and len(requete.zones) > 1:
            zones_cibles = requete.zones
        elif "academie" in ind.niveaux_zone or any(zones().get(z) and zones()[z].niveau == "academie" for z in publiees):
            # Éducation : 16 académies (FR-040)
            zones_cibles = [z.code for z in zones().values() if z.niveau == "academie"]
        else:
            # 14 régions administratives
            zones_cibles = [z.code for z in zones().values() if z.niveau == "region" and z.code != "SN"]

        resultats = []
        defauts = {}
        for z in zones_cibles:
            r = resoudre_un(socle, ind, z, periode, demande, langue, question)
            if not isinstance(r, Introuvable):
                resultats.append(r[0])
                defauts = {k: defauts.get(k, False) or v for k, v in r[1].items()}

        if not resultats:
            return Introuvable("zone_non_couverte", "aucune zone disponible pour le classement")
        if melange := meme_categorie(socle, ind, resultats):
            return melange

        reverse = ordre_effectif(requete, question) == "desc"
        resultats.sort(key=lambda r: r.valeur, reverse=reverse)

        # Mise en évidence de la zone citée si la question en cite une, sinon de la tête
        zone_citee = None
        if requete.zones and len(requete.zones) == 1:
            zone_citee = requete.zones[0]
        else:
            for z_code in zones_cibles:
                z_obj = zones().get(z_code)
                if z_obj and re.search(r"\b" + re.escape(normaliser(z_obj.libelle_fr)) + r"\b", normaliser(question)):
                    zone_citee = z_code
                    break

        if zone_citee and any(r.zone.code == zone_citee for r in resultats):
            for r in resultats:
                r.mise_en_evidence = (r.zone.code == zone_citee)
        else:
            for i, r in enumerate(resultats):
                r.mise_en_evidence = (i == 0)

        graph = graphique_classement(resultats, ind)
        return Resolution(resultats, defauts, graph)

    # -----------------------------------------------------------------------
    # Comparaison (#14) : spatiale (2+ zones) ou temporelle (2 périodes)
    # -----------------------------------------------------------------------
    if requete.intention == "comparaison":
        fin = getattr(requete.periode, "fin", None)
        citees = periodes_citees(question) if not fin else []
        q = normaliser(question)
        evolutif = est_evolution(question)
        if (len(requete.zones or []) <= 1) and (fin or len(citees) >= 2 or evolutif):
            # Comparaison temporelle. Recette du 08/10 : « a-t-il diminué ? », « après 2019 », « sur les dix dernières
            # années », « l'évolution des arrivées en 2017 » ne donnaient qu'une valeur.
            z = requete.zones[0] if (requete.zones and len(requete.zones) == 1) else None
            serie = sorted({o.periode for o in socle.observations(ind.code) if o.zone == zone_de_la_serie(socle, ind.code, z)})
            passees = [x for x in serie if x[:4] <= str(ANNEE_EN_COURS)] or serie
            mode_debut = "fin"
            if fin or len(citees) >= 2:
                p_debut = requete.periode.valeur if requete.periode.valeur else citees[0]
                p_fin = fin or citees[1]
            else:
                p_cite = requete.periode.valeur or (citees[0] if citees else None)
                p_fin = None
                if p_cite and re.fullmatch(r"\d{4}", p_cite) and p_cite not in serie \
                        and not re.search(r"\b(depuis|apres)\b", q):
                    dans = [x for x in serie if x.startswith(p_cite + "-")]  # au fil de l'année, mois par mois
                    p_debut, p_fin = (dans[0], dans[-1]) if len(dans) > 1 else (p_cite, None)
                elif p_cite:
                    p_debut, mode_debut = p_cite, "debut"  # depuis / après : jusqu'à la dernière période
                elif (n := fenetre_periodes(question)) and len(passees) > n:
                    p_debut, p_fin = passees[-1 - n], passees[-1]  # « les douze derniers mois disponibles »
                elif (n := fenetre_annees(question)) and passees:
                    cible = int(passees[-1][:4]) - n
                    p_debut = next((x for x in passees if int(x[:4]) >= cible), passees[0])
                else:
                    p_debut = passees[0] if passees else None
            # une évolution part de l'année publiée la plus proche (« qu'il y a vingt ans » : 2005 si 2006 manque)
            annuelles = [x for x in serie if re.fullmatch(r"\d{4}", x)]
            if evolutif and p_debut and re.fullmatch(r"\d{4}", p_debut) and p_debut not in serie and annuelles:
                p_debut = min(annuelles, key=lambda x: (abs(int(x) - int(p_debut)), x))
            if p_debut and p_fin and p_debut > p_fin:
                p_debut, p_fin = p_fin, p_debut

            r_deb = resoudre_un(socle, ind, z, p_debut, demande, langue, question, annee=mode_debut)
            if isinstance(r_deb, Introuvable):
                return r_deb
            r_fin = resoudre_un(socle, ind, z, p_fin, demande, langue, question)
            if isinstance(r_fin, Introuvable):
                return r_fin
            if r_deb[0].periode.valeur == r_fin[0].periode.valeur:  # une seule période publiée : une seule valeur
                return Resolution([r_fin[0]], r_fin[1], None)

            r_deb[0].mise_en_evidence = True
            r_fin[0].mise_en_evidence = True
            resultats = [r_deb[0], r_fin[0]]
            defauts = {k: r_deb[1].get(k, False) or r_fin[1].get(k, False) for k in ("zone", "periode")}
            graph = graphique_evolution(socle, resultats, ind)
            return Resolution(resultats, defauts, graph)

        # Comparaison spatiale (2+ zones, même période ; ou une année par zone, #212)
        periode = None if requete.periode.type == "derniere" else requete.periode.valeur
        par_zone = periode_par_zone(requete.zones or [], question)
        # deux années citées sans être rattachées chacune à une zone (« à Dakar et Thiès entre 2011 et 2022 ») :
        # chaque zone aux deux années, jamais une seule année servie en silence (#212)
        deux_annees = [] if par_zone or len(requete.zones or []) < 2 else periodes_citees(question)
        couples = ([(z, p) for z in requete.zones for p in deux_annees] if len(deux_annees) == 2
                   else [(z, par_zone.get(z, periode) if par_zone else periode) for z in requete.zones or [None]])
        resultats, defauts = [], {}
        for z, p in couples:
            r = resoudre_un(socle, ind, z, p, demande, langue, question)
            if isinstance(r, Introuvable):
                return r
            r[0].mise_en_evidence = True
            resultats.append(r[0])
            defauts = {k: defauts.get(k, False) or v for k, v in r[1].items()}
        if len(deux_annees) == 2:  # quatre valeurs datées : le texte les donne, un graphique par zone tromperait
            if melange := meme_categorie(socle, ind, resultats):
                return melange
            return Resolution(resultats, defauts, None)
        if len(resultats) > 1 and (melange := meme_categorie(socle, ind, resultats)):
            return melange
        graph = graphique_comparaison_zones(resultats, ind) if len(resultats) > 1 else None
        return Resolution(resultats, defauts, graph)

    # -----------------------------------------------------------------------
    # Valeur unique
    # -----------------------------------------------------------------------
    periode = None if requete.periode.type == "derniere" else requete.periode.valeur
    resultats, defauts = [], {}
    for z in requete.zones or [None]:
        r = resoudre_un(socle, ind, z, periode, demande, langue, question, annee="choix")
        if isinstance(r, Introuvable):
            return r
        resultats.append(r[0])
        defauts = {k: defauts.get(k, False) or v for k, v in r[1].items()}
    graph = None
    if len(resultats) == 1:
        graph = graphique_contexte_valeur(socle, resultats[0], ind)
    return Resolution(resultats, defauts, graph)


def national(socle: Socle, r: Resultat, langue: str = "fr") -> Resultat | None:
    """La valeur nationale publiée qui correspond à un résultat régional : même indicateur, même
    période, mêmes modalités. Lue dans le socle, jamais calculée (position relative, #16)."""
    lignes = socle.observations(r.indicateur.code)
    o = next((x for x in lignes if x.id == r.observation_id), None)
    if o is None or o.zone == "SN":
        return None
    n = next((x for x in lignes if x.zone == "SN" and x.periode == o.periode
              and x.desagregation == o.desagregation), None)
    if n is None:
        return None
    uniques = frozenset(k for k in {k for o in lignes for k, _ in o.desagregation}
                        if len({o.dims().get(k) for o in lignes} - {None}) == 1)
    return resultat(socle, n, indicateurs()[r.indicateur.code], langue, uniques)
