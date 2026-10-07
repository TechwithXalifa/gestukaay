"""Compréhension : question FR / WO -> RequeteStructuree (issue #10, décision 0010).

    comp = Comprehension(charger_client())
    resultat = comp.comprendre("Combien d'habitants à Thiès ?")
    resultat.requete   # RequeteStructuree(intention="valeur", indicateur="pvswjnd", zones=["SN-TH"], …)

Principe : le LLM n'écrit JAMAIS un code.
  1. zones et périodes citées : trouvées sans LLM (référentiel des zones du socle) ;
  2. indicateurs candidats : recherche lexicale, 15 au plus, numérotés ;
  3. le LLM renvoie l'intention, le NUMÉRO du candidat, la période et une
     désagrégation en vocabulaire fixe (sexe, milieu, âge, cycle, produit),
     que la résolution (#11) fait correspondre aux libellés de chaque jeu ;
  4. contrôles : numéro hors liste, période mal formée -> on ne garde pas ;
  5. si aucun fournisseur ne répond : règles locales, sans réseau.
Le LLM ne voit aucune valeur du socle [EF-04].
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from gestukaay_contracts.models import Periode, RequeteStructuree
from gestukaay_socle.indicateurs import indicateurs
from gestukaay_socle.zones import normaliser
from gestukaay_socle.zones import zones as zones_ref
from pydantic import BaseModel, ConfigDict, Field

from .candidats import (
    ORDRE_ASC,
    Candidat,
    aucun_mot_connu,
    desagregation_citee,
    index,
    lieux_inconnus,
    periodes_citees,
    texte_normalise,
    zones_citees,
)
from .llm import Appel, ClientLLM, EchecLLM

K = 15  # candidats proposés au LLM
_NIVEAUX = {"pays": "pays", "region": "régions", "departement": "départements", "academie": "académies"}


class SortieLLM(BaseModel):
    """Ce que le LLM renvoie : aucun code, seulement des choix bornés."""

    model_config = ConfigDict(extra="forbid")
    intention: Literal["valeur", "comparaison", "classement", "hors_perimetre"]
    candidat: int | None = Field(None, description="numéro du candidat qui correspond, ou null")
    periode_type: Literal["annee", "trimestre", "mois", "derniere"] = "derniere"
    periode_valeur: str | None = Field(None, description="2023, 2024-T2 ou 2024-03 ; null si derniere")
    sexe: Literal["femmes", "hommes", "total"] | None = None
    milieu: Literal["urbain", "rural", "total"] | None = None
    age: str | None = Field(None, description="tranche d'âge demandée, ex. 15-24, moins de 15")
    cycle: str | None = Field(None, description="cycle d'enseignement : elementaire, moyen, secondaire…")
    produit: str | None = Field(None, description="produit ou culture précisé, ex. riz, mil")
    confiance: float = Field(ge=0, le=1)
    proches: list[int] = Field(
        default_factory=list,
        description="au plus 3 numéros de candidats réellement liés au thème, ou vide",
    )
    incomprehensible: bool = Field(
        False,
        description="vrai si la question est inintelligible ou incompréhensible",
    )
    periode_fin: str | None = Field(None, description="deuxième période pour une comparaison temporelle, ou null")
    ordre: Literal["desc", "asc"] = Field("desc", description="sens du classement : desc (le plus) ou asc (le moins)")


SYSTEME = """Tu traduis une question sur les statistiques officielles du Sénégal en requête structurée.
La question peut être en français, en wolof ou mélangée, avec des fautes.

On te donne : la question, les zones et périodes déjà repérées, et une liste NUMÉROTÉE d'indicateurs
candidats. Tu ne vois aucune valeur et tu n'en produis jamais.

Réponds :
- intention : « valeur » (une valeur), « comparaison » (plusieurs zones ou plusieurs périodes),
  « classement » (quelle région a le plus / le moins…), « hors_perimetre » (pas une question
  statistique, ou aucun candidat ne parle de ce qui est demandé).
- candidat : le NUMÉRO du candidat qui mesure ce qui est demandé, sinon null.
  Choisis-le MÊME s'il ne couvre pas la zone ou l'année demandées (une réponse approchée sera
  proposée), et même pour une prévision (« quel sera… en 2030 ») : c'est le socle qui dira si la
  valeur est publiée. Un produit précis (riz, mil) peut relever d'un indicateur plus large
  (céréales) : choisis-le et indique le produit.
  Entre plusieurs candidats pertinents, préfère dans l'ordre : celui dont la couverture
  [zones ; années] contient la zone et l'année demandées, puis ceux marqués ★ (vérifiés), puis
  ceux dont l'unité est indiquée et dont la dernière année est la plus récente.
- periode_type / periode_valeur : l'année (2023), le trimestre (2024-T2) ou le mois (2024-03)
  demandés ; « derniere » et null si la question n'en cite pas.
- sexe, milieu, age, cycle, produit : seulement si la question les précise, sinon null.
- confiance : entre 0 et 1.
- proches : si intention est « hors_perimetre » ou en cas de refus, les numéros (au plus 3)
  de candidats de la liste qui sont RÉELLEMENT liés au thème de la question, ou [] si aucun
  n'est pertinent. Ne propose jamais un candidat sans rapport (ex. pour une langue, ne propose
  jamais la prison).
- incomprehensible : true seulement si la question est inintelligible, du charabia ou impossible
  à comprendre (ex. « asdkjh », « euh bon voilà »). Dans ce cas, intention = « hors_perimetre »,
  candidat = null et proches = [].
Si un échange précédent est donné et que la question le prolonge (« Et pour Kaolack ? »,
« Kaolack nak ? »), reprends son indicateur, sauf si la question en demande un autre."""


@dataclass
class Comprise:
    requete: RequeteStructuree
    candidats: list[Candidat]  # servent aussi aux « indicateurs proches » d'un refus (#13)
    source: Literal["llm", "regles"]
    appel: Appel | None = None
    detail: dict = field(default_factory=dict)
    lieux_inconnus: list[str] = field(default_factory=list)  # « Touba » : jamais remplacé par le national
    proches: list[Candidat] = field(default_factory=list)
    incomprehensible: bool = False


_PERIODE = {"annee": r"(19|20)\d\d", "trimestre": r"(19|20)\d\d-T[1-4]", "mois": r"(19|20)\d\d-(0[1-9]|1[0-2])"}


def periode_valide(type_: str, valeur: str | None) -> Periode | None:
    if type_ == "derniere":
        return Periode(type="derniere")
    if valeur and re.fullmatch(_PERIODE[type_], valeur):
        return Periode(type=type_, valeur=valeur)
    return None


def periode_de(valeur: str) -> Periode:
    """« 2023 », « 2024-T2 », « 2024-03 » -> Periode."""
    if "-T" in valeur:
        return Periode(type="trimestre", valeur=valeur)
    return Periode(type="mois" if "-" in valeur else "annee", valeur=valeur)


def couvrant(candidats: list[Candidat], niveaux: set[str]) -> list[Candidat]:
    """Les candidats publiés au niveau des zones citées d'abord, les autres ensuite.
    Le même concept existe souvent dans plusieurs jeux (chômage par région dans dwibrlf,
    national seulement dans muhgux) : servir Dakar exige un jeu qui publie Dakar. Les autres
    restent proposés : « le prix du riz à Thiès » n'existe qu'à Dakar, la réponse sera
    approchée (#12)."""
    ok = [c for c in candidats if niveaux <= set(c.indicateur.niveaux_zone)]
    return ok[:K - 5] + [c for c in candidats if c not in ok][:5] + ok[K - 5:]


_TEMPS = re.compile(r"\b(an|annee|annees|mois|trimestre|dernier|derniere|passe|passee|prochain|prochaine|"
                    r"actuel|actuelle|aujourd|recent|recente|at|atum|weer|ren|daaw|daawat)\b")  # ren, daaw : KBD


# Marqueurs d'une question de suivi (#15, décision 0021). Wolof : écrits par KBD (décision 0009).
_SUIVI_EN_TETE = {"et", "pour", "ak"}  # « Et pour Kaolack ? », « Ak Kaolack ? » (en tête seulement :
#                                        « Chômage Dakar ak Thiès » est une comparaison)
_SUIVI_PARTOUT = {"aussi", "nak", "tamit"}  # « Kaolack aussi ? », « Kaolack nak ? », « Kaolack tamit ? »


def _suivi(question: str) -> bool:
    """Une question courte qui prolonge la précédente."""
    m = texte_normalise(question).split()  # « Kaolack nak? » : ponctuation collée détachée
    return len(m) <= 5 and (m[:1] and m[0] in _SUIVI_EN_TETE or bool(_SUIVI_PARTOUT & set(m))
                            or "meme chose" in " ".join(m))


def precedente_comprise(contexte: list[RequeteStructuree | None] | None) -> RequeteStructuree | None:
    """Le dernier des 3 derniers échanges qui a été compris (un indicateur) : un refus ou une
    incompréhension intercalés ne coupent pas le fil (décision 0021)."""
    return next((r for r in reversed((contexte or [])[-3:]) if r is not None and r.indicateur), None)


def heriter(req: RequeteStructuree, precedente: RequeteStructuree, question: str,
            periodes: list[str]) -> RequeteStructuree:
    """Question de suivi : ce qu'elle ne précise pas est repris de l'échange précédent, ce qu'elle
    cite remplace (EF-09 : « et Kaolack ? » après Thiès en 2019 -> Kaolack en 2019)."""
    if not req.indicateur:
        return req
    maj: dict = {}
    if not req.zones:
        maj["zones"] = list(precedente.zones)
    if not periodes and req.periode.type == "derniere" and not _TEMPS.search(normaliser(question)):
        maj["periode"] = precedente.periode.model_copy()
    if req.indicateur == precedente.indicateur and precedente.desagregation:
        # même indicateur seulement : les dimensions d'un autre jeu peuvent ne pas exister
        maj["desagregation"] = {**precedente.desagregation, **(req.desagregation or {})}
    zones, periode = maj.get("zones", req.zones), maj.get("periode", req.periode)
    if req.intention == "valeur" and (precedente.intention == "classement" or (
            precedente.intention == "comparaison" and (len(zones) > 1 or periode.fin))):
        maj["intention"] = precedente.intention
        maj["ordre"] = precedente.ordre
    return req.model_copy(update=maj)


class Comprehension:
    def __init__(self, client: ClientLLM | None):
        self.client = client  # None : règles locales seulement (essais, secours)

    def comprendre(self, question: str, contexte: list[RequeteStructuree | None] | None = None) -> Comprise:
        zones = zones_citees(question)
        periodes = periodes_citees(question)
        precedente = precedente_comprise(contexte)
        suivi = precedente is not None and _suivi(question)
        niveaux = {zones_ref()[z].niveau for z in zones if z != "SN"}
        if not niveaux and _CLASSEMENT.search(normaliser(question)):
            niveaux = {"region"}  # « quelle région… » : il faut un indicateur publié par région
        candidats = couvrant(index().chercher(question, 4 * K, niveaux), niveaux)[:K]
        if suivi:
            # l'indicateur de l'échange précédent est toujours proposé, en premier
            p = indicateurs().get(precedente.indicateur)
            if p and all(c.indicateur.code != p.code for c in candidats):
                candidats = [Candidat(p, 0.0), *candidats[:K - 1]]
        if self.client is not None:
            try:
                sortie, appel = self.client.structurer(SYSTEME, self._message(question, zones, periodes,
                                                                              candidats, precedente), SortieLLM)
                req = self._requete(sortie, candidats, zones, periodes, precedente, question)
                if suivi:
                    req = heriter(req, precedente, question, periodes)
                proches = [candidats[i - 1] for i in sortie.proches if 1 <= i <= len(candidats)][:3]
                return Comprise(req, candidats, "llm", appel, {"sortie": sortie.model_dump()},
                                lieux_inconnus(question), proches=proches,
                                incomprehensible=sortie.incomprehensible)
            except EchecLLM as e:
                appel = e.appel
        else:
            appel = None
        incomp = aucun_mot_connu(question)
        req = regles(question, candidats, zones, periodes, precedente)
        if suivi:
            req = heriter(req, precedente, question, periodes)
        proches = [] if incomp else [c for c in candidats if c.score >= SEUIL_REGLES][:3]
        return Comprise(req, candidats, "regles", appel,
                        lieux_inconnus=lieux_inconnus(question), proches=proches,
                        incomprehensible=incomp)

    # ------------------------------------------------------------------

    @staticmethod
    def _message(question, zones, periodes, candidats, precedente) -> str:
        lignes = [f"Question : {question}",
                  f"Zones repérées : {', '.join(zones) or 'aucune'}",
                  f"Périodes repérées : {', '.join(periodes) or 'aucune'}"]
        if precedente and precedente.indicateur:
            p = indicateurs().get(precedente.indicateur)
            lignes.append(f"Échange précédent : {p.libelle_fr if p else precedente.indicateur}, "
                          f"zones {', '.join(precedente.zones) or 'Sénégal'}")
        lignes.append("Candidats :")
        for n, c in enumerate(candidats, 1):
            x = c.indicateur
            unite = x.unite_affichee or x.unite
            etoile = "★ " if x.verification == "verifie" else ""
            couverture = ", ".join(_NIVEAUX[n_] for n_ in x.niveaux_zone) or "national"
            lignes.append(f"{n}. {etoile}{x.libelle_fr} ({unite or 'unité non précisée'}) — jeu : {x.jeu} "
                          f"[{couverture} ; {x.periode_debut}–{x.periode_fin}]")
        return "\n".join(lignes)

    @staticmethod
    def _requete(s: SortieLLM, candidats, zones, periodes, precedente, question) -> RequeteStructuree:
        code = None
        if s.candidat is not None and 1 <= s.candidat <= len(candidats):
            code = candidats[s.candidat - 1].indicateur.code
        intention = s.intention if code or s.intention == "hors_perimetre" else "hors_perimetre"
        # les périodes repérées dans le texte priment ; celle du LLM n'est prise que si la question
        # parle du temps (« l'an dernier ») : sinon il en déduit une du nom du jeu (« RGPH-5, 2023 »)
        if periodes:
            periode = periode_de(periodes[0])
            if len(periodes) > 1:
                periode.fin = periodes[1]
        elif _TEMPS.search(normaliser(question)):
            periode = periode_valide(s.periode_type, s.periode_valeur) or Periode(type="derniere")
            if s.periode_fin:
                periode.fin = s.periode_fin
        else:
            periode = Periode(type="derniere")
        if not zones and precedente and _suivi(question):
            zones = list(precedente.zones)
        desag = {k: v for k, v in (("sexe", s.sexe), ("milieu", s.milieu), ("age", s.age),
                                   ("cycle", s.cycle), ("produit", s.produit)) if v}
        return RequeteStructuree(intention=intention, indicateur=code if intention != "hors_perimetre" else None,
                                 zones=zones, periode=periode, desagregation=desag or None,
                                 ordre=s.ordre, confiance=round(s.confiance, 2))


# --------------------------------------------------------------------------
# Règles locales : sans réseau ni modèle (secours, et base de comparaison)
# --------------------------------------------------------------------------

SEUIL_REGLES = 6.0  # score BM25 minimal pour oser un indicateur sans LLM
_CLASSEMENT = re.compile(r"\b(le|la|les) (plus|moins)\b|\bquelle region\b|\bclasse(ment)?\b"
                         r"|\b(diiwaan|diwaan|region)\b.*\b(epp|gena|geuna)\b|\bban (region|diiwaan|diwaan)\b")
_COMPARAISON = re.compile(r"\bcompar|\bentre\b|\bevolution\b|\b(augmente|baisse)\b"
                          r"|\b(yokk|yokku|wanniku|suufe|diggante)\b")  # wolof (KBD) : augmenter, baisser, entre


def regles(question: str, candidats: list[Candidat], zones: list[str], periodes: list[str],
           precedente: RequeteStructuree | None) -> RequeteStructuree:
    if aucun_mot_connu(question):
        return RequeteStructuree(intention="hors_perimetre", zones=zones, confiance=0.1)
    t = texte_normalise(question)  # « ŋ » et ponctuation collée, comme les candidats
    meilleur = max(candidats, key=lambda c: c.score, default=None)  # le tri par couverture ne compte pas ici
    meilleur = meilleur if meilleur and meilleur.score >= SEUIL_REGLES else None
    code = meilleur.indicateur.code if meilleur else None
    if precedente and precedente.indicateur and _suivi(question):
        code = code if code and not zones else precedente.indicateur
        zones = zones or list(precedente.zones)
    if code is None:
        return RequeteStructuree(intention="hors_perimetre", zones=zones, confiance=0.3)
    suivi = bool(precedente) and _suivi(question)
    if _CLASSEMENT.search(t):
        intention = "classement"
    elif (len(zones) > 1 and not suivi) or len(periodes) > 1 or _COMPARAISON.search(t):
        intention = "comparaison"
    else:
        intention = "valeur"
    ordre = "asc" if ORDRE_ASC.search(t) else "desc"
    if len(periodes) > 1:
        periode = periode_de(periodes[0])
        periode.fin = periodes[1]
    elif periodes:
        periode = periode_de(periodes[0])
    else:
        periode = Periode(type="derniere")
    return RequeteStructuree(intention=intention, indicateur=code, zones=zones, periode=periode,
                             desagregation=desagregation_citee(question) or None, ordre=ordre, confiance=0.4)
