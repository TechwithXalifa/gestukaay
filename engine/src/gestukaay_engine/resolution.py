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
from datetime import date
from functools import cache
from typing import Literal

from gestukaay_contracts.models import (
    PeriodeResolue,
    RefIndicateur,
    RefZone,
    RequeteStructuree,
    Resultat,
    Source,
)
from gestukaay_socle.indicateurs import REFERENTIELS, Indicateur, indicateurs
from gestukaay_socle.zones import normaliser, zones

from .socle import Observation, Socle

Raison = Literal["indicateur_inconnu", "zone_non_couverte", "periode_absente", "desagregation_absente",
                 "desagregation_ambigue", "non_traite"]

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


@dataclass
class Introuvable:
    raison: Raison
    detail: str
    disponibles: list[str] = field(default_factory=list)  # zones ou périodes publiées
    choix: dict[str, list[str]] = field(default_factory=dict)  # dimension ambiguë -> modalités


# --------------------------------------------------------------------------
# Désagrégation
# --------------------------------------------------------------------------

def est_total(modalite: str) -> bool:
    return normaliser(modalite) in _TOTAUX


def _nombres(texte: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", texte)]


def correspond(canonique: str, valeur: str, modalite: str) -> bool:
    """La modalité du jeu correspond-elle à la valeur canonique (« femmes » ~ « Féminin ») ?"""
    m, v = normaliser(modalite), normaliser(valeur)
    if v == "total":
        return m in _TOTAUX
    for groupe in _VALEURS.values():  # « primaire » ~ « Elémentaire », « filles » ~ « Féminin »
        if v in groupe:
            return m in groupe or bool(set(m.split()) & groupe)
    if canonique == "age":
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


def citee(modalite: str, question: str) -> bool:
    """La modalité est-elle nommée dans la question (« Pêche artisanale », « Français ») ?"""
    m, q = normaliser(modalite).split(), f" {normaliser(question)} "
    return bool(m) and len("".join(m)) >= 3 and f" {' '.join(m)} " in q


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
                return [], Introuvable("desagregation_absente", f"{canon} = {valeur} : non publié pour cet indicateur")
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


def formater(v: float) -> str:
    """2463677 -> « 2 463 677 » (espace fine insécable U+202F) ; 25.7 -> « 25,7 »."""
    if v == int(v) or abs(v) >= 1000:
        texte = f"{round(v):,}"
    elif abs(v) >= 100:
        texte = f"{v:,.0f}"
    else:
        texte = f"{v:,.2f}".rstrip("0").rstrip(".") if abs(v) < 1 else f"{v:,.1f}"
    return texte.replace(",", " ").replace(".", ",")


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


def source(socle: Socle, o: Observation, ind: Indicateur) -> Source:
    s = socle.sources.get(o.source_id)
    publie = (s.date_publication if s and s.date_publication else None) or date(1970, 1, 1)
    producteur = (s.producteur if s else "") or ind.producteur
    operation = _operations().get(o.source_id, "")
    licence = s.licence if s else ""
    libelle = " · ".join(x for x in (producteur, operation, f"publié le {_date_fr(publie)}", licence) if x)
    return Source(producteur=producteur, operation=operation, titre=(s.titre if s else ind.jeu),
                  date_publication=publie, licence=licence, url=s.url if s else "", libelle=libelle)


def ref_zone(code: str) -> RefZone:
    z = zones()[code]
    libelle = f"académie de {z.libelle_fr}" if z.niveau == "academie" and not normaliser(
        z.libelle_fr).startswith(("academie", "ia ")) else z.libelle_fr
    return RefZone(code=code, libelle=libelle, niveau=z.niveau)


def resultat(socle: Socle, o: Observation, ind: Indicateur, langue: str = "fr") -> Resultat:
    desag = {k: v for k, v in o.desagregation if not est_total(v)}
    libelle = (ind.libelle_wo if langue == "wo" and ind.libelle_wo else ind.libelle_fr)
    return Resultat(
        indicateur=RefIndicateur(code=ind.code, libelle=libelle), zone=ref_zone(o.zone),
        periode=PeriodeResolue(valeur=o.periode, libelle=libelle_periode(o.periode)),
        desagregation=desag or None, valeur=o.valeur, valeur_affichee=formater(o.valeur),
        unite=ind.unite_affichee or ind.unite or o.unite, source=source(socle, o, ind),
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
    return all(f" {m} " in texte for m in normaliser(valeur).split())


def resoudre_un(socle: Socle, ind: Indicateur, zone: str | None, periode: str | None,
                demande: dict[str, str], langue: str = "fr",
                question: str = "") -> tuple[Resultat, dict] | Introuvable:
    """Une valeur : indicateur × zone × période × désagrégation."""
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
        return Introuvable("zone_non_couverte", f"{zone} non publié", disponibles=publiees)
    demande = {k: v for k, v in demande.items() if not portee_par_indicateur(ind, v)}
    # 1. ce que la question demande (riz : seule année publiée à Kaolack, 2016) ;
    # 2. la période ; 3. les autres dimensions, ambiguës seulement si plusieurs modalités existent cette année-là
    lignes, erreur = imposer([o for o in lignes if o.zone == zone], demande)
    if erreur:
        return erreur
    periodes = sorted({o.periode for o in lignes})
    p = periode or periodes[-1]
    if p not in periodes:
        return Introuvable("periode_absente", f"{p} non publié", disponibles=periodes)
    retenues, erreur = completer([o for o in lignes if o.periode == p], question,
                                 defauts_desagregation().get(ind.dataset_id))
    if erreur:
        return erreur
    if len({o.desagregation for o in retenues}) > 1:  # ne devrait pas arriver après choisir()
        return Introuvable("desagregation_ambigue", "plusieurs lignes pour la même clé")
    return resultat(socle, retenues[0], ind, langue), defauts


def resoudre(socle: Socle, requete: RequeteStructuree, langue: str = "fr", question: str = "",
             lieux_inconnus: list[str] | None = None) -> Resolution | Introuvable:
    """Intentions « valeur » et « comparaison » (plusieurs zones). Le classement relève de #14.
    lieux_inconnus : lieux cités mais absents du référentiel (« Touba », « la ville de Thiès ») :
    jamais remplacés par le national."""
    if lieux_inconnus:
        return Introuvable("zone_non_couverte", "lieu hors référentiel : " + ", ".join(lieux_inconnus))
    if requete.intention == "classement":
        return Introuvable("non_traite", "classement : #14")
    if requete.intention == "hors_perimetre" or not requete.indicateur:
        return Introuvable("indicateur_inconnu", "hors périmètre")
    ind = indicateurs().get(requete.indicateur)
    if ind is None:
        return Introuvable("indicateur_inconnu", f"{requete.indicateur} : code inconnu du référentiel")
    periode = None if requete.periode.type == "derniere" else requete.periode.valeur
    demande = dict(requete.desagregation or {})
    resultats, defauts = [], {}
    for z in requete.zones or [None]:
        r = resoudre_un(socle, ind, z, periode, demande, langue, question)
        if isinstance(r, Introuvable):
            return r
        resultats.append(r[0])
        defauts = {k: defauts.get(k, False) or v for k, v in r[1].items()}
    return Resolution(resultats, defauts)
