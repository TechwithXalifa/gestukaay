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

from .candidats import Candidat, index, periodes_citees, zones_citees
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


SYSTEME = """Tu traduis une question sur les statistiques officielles du Sénégal en requête structurée.
La question peut être en français, en wolof ou mélangée, avec des fautes.

On te donne : la question, les zones et périodes déjà repérées, et une liste NUMÉROTÉE d'indicateurs
candidats. Tu ne vois aucune valeur et tu n'en produis jamais.

Réponds :
- intention : « valeur » (une valeur), « comparaison » (plusieurs zones ou plusieurs périodes),
  « classement » (quelle région a le plus / le moins…), « hors_perimetre » (pas une question
  statistique, ou aucun candidat ne correspond à ce qui est demandé).
- candidat : le NUMÉRO du candidat qui correspond exactement à ce qui est demandé, sinon null.
  Ne juge pas si la donnée existe pour la zone ou l'année : choisis seulement l'indicateur.
  Les candidats marqués ★ sont vérifiés : à pertinence égale, préfère-les.
- periode_type / periode_valeur : l'année (2023), le trimestre (2024-T2) ou le mois (2024-03)
  demandés ; « derniere » et null si la question n'en cite pas.
- sexe, milieu, age, cycle, produit : seulement si la question les précise, sinon null.
- confiance : entre 0 et 1.
Si un échange précédent est donné et que la question le prolonge (« Et pour Kaolack ? »,
« Kaolack nak ? »), reprends son indicateur, sauf si la question en demande un autre."""


@dataclass
class Comprise:
    requete: RequeteStructuree
    candidats: list[Candidat]  # servent aussi aux « indicateurs proches » d'un refus (#13)
    source: Literal["llm", "regles"]
    appel: Appel | None = None
    detail: dict = field(default_factory=dict)


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
                    r"actuel|actuelle|aujourd|recent|recente|at|atum|weer)\b")


def _suivi(question: str) -> bool:
    """« Et pour Kaolack ? », « Kaolack nak ? » : une question courte qui prolonge la précédente."""
    m = normaliser(question).split()
    return len(m) <= 5 and (m[:1] == ["et"] or "nak" in m)


class Comprehension:
    def __init__(self, client: ClientLLM | None):
        self.client = client  # None : règles locales seulement (essais, secours)

    def comprendre(self, question: str, contexte: list[RequeteStructuree] | None = None) -> Comprise:
        zones = zones_citees(question)
        periodes = periodes_citees(question)
        precedente = (contexte or [None])[-1]
        niveaux = {zones_ref()[z].niveau for z in zones if z != "SN"}
        if not niveaux and _CLASSEMENT.search(normaliser(question)):
            niveaux = {"region"}  # « quelle région… » : il faut un indicateur publié par région
        candidats = couvrant(index().chercher(question, 4 * K, niveaux), niveaux)[:K]
        if precedente and precedente.indicateur and _suivi(question):
            # l'indicateur de l'échange précédent est toujours proposé, en premier
            p = indicateurs().get(precedente.indicateur)
            if p and all(c.indicateur.code != p.code for c in candidats):
                candidats = [Candidat(p, 0.0), *candidats[:K - 1]]
        if self.client is not None:
            try:
                sortie, appel = self.client.structurer(SYSTEME, self._message(question, zones, periodes,
                                                                              candidats, precedente), SortieLLM)
                req = self._requete(sortie, candidats, zones, periodes, precedente, question)
                return Comprise(req, candidats, "llm", appel, {"sortie": sortie.model_dump()})
            except EchecLLM as e:
                appel = e.appel
        else:
            appel = None
        return Comprise(regles(question, candidats, zones, periodes, precedente), candidats, "regles", appel)

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
            lignes.append(f"{n}. {etoile}{x.libelle_fr}{f' ({unite})' if unite else ''} — jeu : {x.jeu} "
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
        elif _TEMPS.search(normaliser(question)):
            periode = periode_valide(s.periode_type, s.periode_valeur) or Periode(type="derniere")
        else:
            periode = Periode(type="derniere")
        if not zones and precedente and _suivi(question):
            zones = list(precedente.zones)
        desag = {k: v for k, v in (("sexe", s.sexe), ("milieu", s.milieu), ("age", s.age),
                                   ("cycle", s.cycle), ("produit", s.produit)) if v}
        return RequeteStructuree(intention=intention, indicateur=code if intention != "hors_perimetre" else None,
                                 zones=zones, periode=periode, desagregation=desag or None,
                                 confiance=round(s.confiance, 2))


# --------------------------------------------------------------------------
# Règles locales : sans réseau ni modèle (secours, et base de comparaison)
# --------------------------------------------------------------------------

SEUIL_REGLES = 6.0  # score BM25 minimal pour oser un indicateur sans LLM
_CLASSEMENT = re.compile(r"\b(le|la|les) (plus|moins)\b|\bquelle region\b|\bclasse(ment)?\b"
                         r"|\bdiiwaan\b.*\b(epp|gena|geuna)\b|\bban region\b")
_COMPARAISON = re.compile(r"\bcompar|\bentre\b|\bevolution\b|\b(augmente|baisse)\b")


def regles(question: str, candidats: list[Candidat], zones: list[str], periodes: list[str],
           precedente: RequeteStructuree | None) -> RequeteStructuree:
    t = normaliser(question)
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
    periode = periode_de(periodes[0]) if periodes else Periode(type="derniere")
    return RequeteStructuree(intention=intention, indicateur=code, zones=zones, periode=periode, confiance=0.4)
