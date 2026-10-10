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

import csv
import re
from dataclasses import dataclass, field
from functools import cache
from typing import Literal

from gestukaay_contracts.models import Periode, RequeteStructuree
from gestukaay_socle.indicateurs import indicateurs
from gestukaay_socle.zones import normaliser
from gestukaay_socle.zones import resoudre as resoudre_zone
from gestukaay_socle.zones import zones as zones_ref
from pydantic import BaseModel, ConfigDict, Field

from .approchee import REFERENTIELS
from .candidats import (
    _MOIS,
    _SYN,
    ORDRE_ASC,
    Candidat,
    aucun_mot_connu,
    desagregation_citee,
    est_evolution,
    extremum,
    forme,
    index,
    lieux_inconnus,
    milieu_cite,
    mots,
    periodes_citees,
    texte_normalise,
    zones_citees,
)
from .conversation import Categorie
from .conversation import regles as conversation_regles
from .langue import _FR, _WO, _WO_FORTS, detecter
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
    conversation: Categorie | None = Field(
        None, description="catégorie si le message n'est pas une demande de chiffre, sinon null (0033)")


SYSTEME = """Tu traduis une question sur les statistiques officielles du Sénégal en requête structurée.
La question peut être en français, en wolof ou mélangée, avec des fautes.

On te donne : la question, les zones et périodes déjà repérées, et une liste NUMÉROTÉE d'indicateurs
candidats. Tu ne vois aucune valeur et tu n'en produis jamais.

Vocabulaire wolof (validé par un locuteur natif) :
- « dëkk yi » = les villes (milieu urbain) ; « all bi » = la campagne (milieu rural) ; « dëkkuwaay » = urbanisation.
  La part de la population qui vit en ville (« ñata ci téeméer… ñoo dëkk ci dëkk yi », « ban wall… ») est le taux
  d'urbanisation, et celle qui vit à la campagne (« ci all bi ») son complément : choisis le taux d'urbanisation.
- « yamadi » = inégalités (indice de Gini) ; « koom-koom » = économie.
- « dee », « deeg » = décès, mortalité : « deeg xale yi » = mortalité des enfants, pas leur croissance.
- « ñakk » (vaccin) n'est pas « ñàkk » (manquer, pauvreté) : « ñakkug xale yi », « ñakk ba mu mat » = vaccination
  (complète) des enfants.
- « yeex a màgg » = retard de croissance ; « njàng », « jàng » = scolarisation ; « ndongo » = élèves.
- « dugub » = mil ; « ceeb » = riz ; « ceeb bu ñu damm » = riz brisé ; « pepp » = céréales.

Réponds :
- intention : « valeur » (une valeur), « comparaison » (plusieurs zones ou plusieurs périodes),
  « classement » (quelle région a le plus / le moins…), « hors_perimetre » (pas une question
  statistique, ou aucun candidat ne parle de ce qui est demandé).
- candidat : le NUMÉRO du candidat qui mesure ce qui est demandé, sinon null.
  Choisis-le MÊME s'il ne couvre pas la zone ou l'année demandées (une réponse approchée sera
  proposée), et même pour une prévision (« quel sera… en 2030 ») : c'est le socle qui dira si la
  valeur est publiée. Un produit précis (riz, mil) peut relever d'un indicateur plus large
  (céréales) : choisis-le et indique le produit.
  Un candidat qui ne mesure pas la chose demandée n'est jamais pertinent, même s'il couvre l'année :
  pour « la recette touristique en 2022 », les recettes du tourisme (jusqu'en 2018), jamais les
  recettes contentieuses (2022) ; le socle proposera les années publiées.
  Entre plusieurs candidats pertinents, préfère dans l'ordre : celui dont la couverture
  [zones ; années] contient la zone et l'année demandées, puis ceux marqués ★ (vérifiés), puis,
  pour une année passée ou la dernière donnée, une valeur OBSERVÉE (recensement, enquête, registre)
  plutôt qu'un jeu marqué « projection », puis ceux dont l'unité est indiquée.
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
- conversation : null dès que le message demande un chiffre. Sinon sa catégorie : « salutation »
  (bonjour, ça va, naka nga def), « remerciement », « au_revoir », « a_propos » (qui es-tu, d'où
  viennent tes chiffres), « langue » (tu parles wolof ?), « aide » (que puis-je demander ?),
  « definition » (c'est quoi tel indicateur : donne aussi son candidat), « pourquoi » (causes,
  analyse, opinion : donne aussi le candidat lié s'il existe), « hors_sujet » (météo, sport,
  politique, poème, conseils…), « impoli ». Une demande de CHIFFRE que les candidats n'ont pas
  (« combien de personnes parlent sérère ») n'est pas hors sujet : conversation = null. Une salutation suivie d'une question de chiffre
  (« Salam, ñaata nit ñoo dëkk Tiés ? ») est une question : conversation = null.
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
    conversation: str | None = None  # catégorie de conversation (0033), sinon None


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
    """Le dernier des 3 derniers échanges qui a été compris (un indicateur). Une incompréhension ou une formule de
    conversation (requête vide) ne coupe pas le fil (décision 0021). Un refus d'une vraie question (requête sans
    indicateur) le coupe : l'usager a changé de sujet (#281 : « On est combien au Sénégal ? » refusé, puis
    « Et à Dakar ? » servait le prix du mil d'un échange plus ancien) — amendement de la 0021 à valider par KBD."""
    for r in reversed((contexte or [])[-3:]):
        if r is None:
            continue
        return r if r.indicateur else None
    return None


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


# Une demande de chiffre n'est jamais du hors sujet (passe Gemini du 07/10, FR-071) : si le socle ne l'a pas,
# c'est un refus « donnée absente », avec « Suggérer cet indicateur à l'équipe ».
_DEMANDE_DE_CHIFFRE = re.compile(r"^(combien|quel est le (nombre|taux|pourcentage|prix|montant)|quelle est la "
                                 r"(part|proportion|population)|naata|nata|niata|gnaa?ta|nyaa?ta|ban tolluwaay)\b")


@cache
def _natures() -> dict[str, set[str]]:
    """dataset -> {« toutes », « en_partie »} d'après socle/referentiels/natures.csv (décision 0007)."""
    out: dict[str, set[str]] = {}
    with (REFERENTIELS / "natures.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["nature"] == "projection":
                out.setdefault(r["dataset_id"], set()).add(
                    "toutes" if not (r["periode_debut"] or r["periode_fin"]) else "en_partie")
    return out


def projection(dataset_id: str) -> str | None:
    """« toutes » si le jeu n'est que projection, « en_partie » s'il en contient, sinon None."""
    n = _natures().get(dataset_id, set())
    return "toutes" if "toutes" in n else "en_partie" if n else None


IDF_NOMME = 5.0  # « condamnées » (7,4), « être » de bien-être (5,7) ; pas « nombre » (2,9) ni « bien » (3,1)


def _nomme_par_la_question(choisi, tete, question: str) -> bool:
    """Recette du 08/10 : le LLM avait raison (« personnes condamnées », « indice de bien-être ») et A2 le
    remplaçait par la tête vérifiée (« personnes emprisonnées », « indice de Gini »). Un mot rare de la question
    présent dans le LIBELLÉ du choix et absent de celui de la tête : la question nomme le choix, on le garde."""
    lib_choisi, lib_tete = set(mots(choisi.libelle_fr)), set(mots(tete.libelle_fr))
    ix = index()
    return any(ix.idf.get(m, 0) >= IDF_NOMME and m in lib_choisi and m not in lib_tete for m in ix.requete(question))


def _verifie_en_tete(code: str | None, candidats, zones, periodes, question: str = "") -> str | None:
    """A2 (passe du 07/10) : le LLM prend parfois un doublon (projection de 2013 au lieu du RGPH-5, jeu arrêté
    en 2023 au lieu de 2025). S'il choisit un indicateur NON vérifié alors que le premier candidat est un
    indicateur vérifié du même domaine qui couvre la zone et l'année demandées, on prend le vérifié."""
    tete = candidats[0].indicateur if candidats else None
    choisi = indicateurs().get(code) if code else None
    if not (tete and choisi) or tete.code == choisi.code:
        return code
    if choisi.verification == "verifie" or tete.verification != "verifie" or tete.domaine != choisi.domaine:
        return code
    if _nomme_par_la_question(choisi, tete, question):
        return code
    niveaux = {zones_ref()[z].niveau for z in zones if z != "SN" and z in zones_ref()}
    if not niveaux <= set(tete.niveaux_zone) and niveaux:
        return code
    if any(not (tete.periode_debut[:4] <= p[:4] <= tete.periode_fin[:4]) for p in periodes):
        return code
    # dernière donnée : un choix observé qui va plus loin dans le temps n'est pas remplacé par plus ancien
    # (revue de SAN) ; une projection, si (RGPH-5 2023 plutôt que la projection de 2013 jusqu'en 2025)
    if not periodes and choisi.periode_fin[:4] > tete.periode_fin[:4] and projection(choisi.dataset_id) is None:
        return code
    return tete.code


RAPPORT_HORS_SUJET = 1.5  # le premier candidat doit dominer nettement le choix du LLM
IDF_DISTINCTIF = 4.0  # mot rare du référentiel (« touristique »), pas « taux » ni « nombre »


def _hors_sujet(code: str | None, candidats, question: str) -> str | None:
    """#156 (passe de SAN du 08/10) : le LLM prenait « Recettes contentieuses » (2012-2023) pour « la recette
    touristique en 2022 » parce qu'elles couvrent 2022, alors que « Recettes — Bulletin touristique » (jusqu'en
    2018) est en tête. Si le premier candidat domine nettement le choix du LLM et porte un mot rare de la
    question que le choix n'a pas, on prend le premier : un chiffre hors sujet est pire qu'une approchée."""
    tete = candidats[0] if candidats else None
    if not (tete and code) or tete.indicateur.code == code:
        return code
    choisi = next((c for c in candidats if c.indicateur.code == code), None)
    if choisi is None or tete.score < RAPPORT_HORS_SUJET * choisi.score:
        return code
    ix = index()
    d_tete, d_choisi = ix.mots_de(tete.indicateur.code), ix.mots_de(code)
    # les mots écrits seulement, pas leurs synonymes : « dëkk » apportait « askan », et la population remplaçait
    # le taux d'urbanisation que le LLM avait bien choisi (questions wolof de KBD, 08/10)
    if any(ix.idf.get(m, 0) >= IDF_DISTINCTIF and m in d_tete and m not in d_choisi for m in set(mots(question))):
        return tete.indicateur.code
    return code


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
                req = _intention_de_la_question(self._requete(sortie, candidats, zones, periodes, precedente, question),
                                                question, zones)
                if (req.indicateur and not suivi and detecter(question) == "fr"
                        and (ind := indicateurs().get(req.indicateur)) and ind.verification != "verifie"
                        and not sujet_dans_la_question(req.indicateur, question, precisions=True)):
                    # 410 questions du 08/10 : « l'ensemble de la période » -> « Ensemble garçon » (un vêtement), « les
                    # prix » -> « Titres autres qu'actions ». Un indicateur non vérifié dont le sujet n'est pas dans la
                    # question n'est pas servi (le wolof est épargné : le lexique ne le couvre pas encore assez)
                    req = req.model_copy(update={"indicateur": None, "intention": "hors_perimetre"})
                if suivi:
                    req = heriter(req, precedente, question, periodes)
                proches = [candidats[i - 1] for i in sortie.proches if 1 <= i <= len(candidats)][:3]
                # une forme sûre des règles (salutations de KBD, merci…) prime sur un « incompréhensible » du LLM :
                # « naka leu » seul lui est opaque (essai du 07/10)
                # sauf le hors sujet quand le LLM a trouvé un indicateur (« recette touristique ») ; définition et
                # « pourquoi » restent rattrapés, le LLM y donne justement un candidat (revue de SAN sur #147)
                regle = sortie.conversation or conversation_regles(question)
                conv = None if regle == "hors_sujet" and req.indicateur and not sortie.conversation else regle
                chiffre = bool(_DEMANDE_DE_CHIFFRE.search(normaliser(question)))
                if conv == "hors_sujet" and chiffre:
                    conv = None  # « Combien de personnes parlent sérère ? » : un chiffre absent, pas du hors sujet
                # une demande de chiffre n'est pas incompréhensible non plus (revue de SAN sur #149)
                return Comprise(req, candidats, "llm", appel, {"sortie": sortie.model_dump()},
                                lieux_inconnus(question), proches=proches,
                                incomprehensible=sortie.incomprehensible and conv is None and not chiffre,
                                conversation=conv)
            except EchecLLM as e:
                appel = e.appel
        else:
            appel = None
        incomp = aucun_mot_connu(question)
        req = regles(question, candidats, zones, periodes, precedente)
        if suivi:
            req = heriter(req, precedente, question, periodes)
        proches = [] if incomp else [c for c in candidats if c.score >= SEUIL_REGLES][:3]
        conv = conversation_regles(question)
        return Comprise(req, candidats, "regles", appel,
                        lieux_inconnus=lieux_inconnus(question), proches=proches,
                        incomprehensible=incomp and conv is None, conversation=conv)

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
            proj = {"toutes": " — projection", "en_partie": " — en partie projection"}.get(projection(x.dataset_id), "")
            lignes.append(f"{n}. {etoile}{x.libelle_fr} ({unite or 'unité non précisée'}) — jeu : {x.jeu}{proj} "
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
            if s.periode_fin and re.fullmatch(r"\d{4}(?:-\d{2}|-T[1-4])?", s.periode_fin):  # #266 : jamais « precedent »
                periode.fin = s.periode_fin
        else:
            periode = Periode(type="derniere")
        if not zones and precedente and _suivi(question):
            zones = list(precedente.zones)
        desag = {k: v for k, v in (("sexe", s.sexe), ("milieu", s.milieu), ("age", s.age),
                                   ("cycle", s.cycle), ("produit", s.produit)) if v}
        # B (passe du 07/10) : une précision que la question cite aussi selon les règles prend la forme des
        # règles, vocabulaire validé (« moins de 5 » et non « 0-5 ») ; les autres restent, le moteur les
        # écarte si la question ne les cite pas et que le jeu ne les publie pas (moteur._sans_precision_inventee)
        desag |= {k: v for k, v in desagregation_citee(question).items() if k in desag}
        code = _hors_sujet(_verifie_en_tete(code, candidats, zones, periodes, question), candidats, question)
        return RequeteStructuree(intention=intention, indicateur=code if intention != "hors_perimetre" else None,
                                 zones=zones, periode=periode, desagregation=desag or None,
                                 ordre=s.ordre, confiance=round(s.confiance, 2))


def _intention_de_la_question(req: RequeteStructuree, question: str, zones: list[str]) -> RequeteStructuree:
    """Ce que la question dit sans ambiguïté prime sur l'intention du LLM (recette du 08/10) :
    - « toutes les régions », « par région » : un classement, pas le total du Sénégal ;
    - un classement sans aucun mot de classement, pour une question qui ne cite que le Sénégal (« Ñi amul ligéey
      ci Senegaal ? » donnait les 14 régions, WO-002) : une valeur."""
    if not req.indicateur:
        return req
    t = normaliser(question)
    if extremum(question) and len(req.zones) <= 1:
        return req.model_copy(update={"intention": "valeur"})  # « quel mois le plus… » : une période, pas des régions
    if _TOUTES_REGIONS.search(t) and req.intention != "classement" and set(req.zones) <= {"SN"}:
        return req.model_copy(update={"intention": "classement", "zones": []})
    if req.intention == "classement" and not _CLASSEMENT.search(t) and zones == ["SN"]:
        return req.model_copy(update={"intention": "valeur", "zones": ["SN"]})
    if req.intention == "valeur" and est_evolution(question) and len(req.zones) <= 1:
        return req.model_copy(update={"intention": "comparaison"})  # « a-t-elle diminué ? », « depuis 2016 »
    return req


# --------------------------------------------------------------------------
# Règles locales : sans réseau ni modèle (secours, et base de comparaison)
# --------------------------------------------------------------------------

SEUIL_REGLES = 6.0  # score BM25 minimal pour oser un indicateur sans LLM

# Secours prudent (recette du 08/10) : sans LLM, un mot qui partage ses lettres avec un libellé suffisait. « Salaire
# du président » donnait le salaire moyen, « dette publique » les dépenses d'éducation (« hors service de la
# dette »), « voitures électriques » un indice de location de voitures. Un chiffre vrai pour une autre question
# est pire qu'un refus avec suggestions : sans LLM, on ne sert un indicateur que si (a) son sujet est dans la
# question et (b) chaque mot porteur de sens de la question se retrouve dans l'indicateur.
_CADRE = {  # mots de la question qui ne disent pas QUOI mesurer
    "taux", "nombre", "combien", "part", "proportion", "pourcentage", "niveau", "total", "totale", "valeur",
    "chiffre", "statistique", "donnee", "indicateur", "pays", "region", "departement", "commune", "ville",
    "annee", "an", "ans", "mois", "trimestre", "dernier", "derniere", "actuel", "actuelle", "actuellement",
    "aujourd", "hui", "compare", "comparer", "comparaison", "evolution", "classement", "classe", "difference",
    "toute", "tou", "tout", "chaque", "depui", "jusqu", "moyen", "moyenne", "quel", "quelle", "svp", "stp",
    "merci", "bonjour", "salut", "voudrai", "veux", "aimerai", "savoir", "connaitre", "dire", "donner", "donne",
    "donnez", "plait", "vou", "je", "tu", "nou", "peux", "pouvez", "cherche", "sui", "etre", "avoir", "senegal",
    "senegaal", "officiel", "officielle", "publie", "selon", "enquete", "disponible", "source", "journaliste",
    "article", "etudiant", "recent", "recente", "eleve", "elevee", "faible", "bas", "haut", "grand", "petit",
    "meilleur", "pire", "baisse", "hausse", "augmente", "augmentation", "diminution", "dan", "ya", "il", "elle",
    "sont", "est", "sera", "etait", "ete", "maintenant", "now", "nombreux", "beaucoup",
    "mettre", "compte", "compter", "compten", "vit", "vivent", "dekk", "deuk", "nekk", "nek", "am", "amul",
    "lim", "limu", "laaj", "xam", "bari", "tollu", "mujj", "rural", "urbain", "rurale", "urbaine", "milieu",
    "personne", "gens", "individu",
    "femme", "homme", "fille", "garcon", "jeune", "age", "elementaire", "primaire", "secondaire", "cycle",
    "jigeen", "goor", "ndaw", "mag", "xale", "atum", "ren", "daaw", "tey", "prochaine", "prochain", "passee",
    "passe", "cette", "seront", "futur", "future", "avenir", "acces", "accede", "dispose", "disposent",
    "beneficie", "utilise", "utilisent", "concerne", "touche", "parmi",
    # wolof (vocabulaire de KBD, test_vocabulaire_wolof) : région, le plus / le moins, manquer de
    "diwaan", "diiwaan", "neew", "tuuti", "gena", "geuna", "rey", "nakk", "ngi",
    # unités, quantités et repères de comparaison
    "kilo", "kg", "litre", "tonne", "quantite", "produit", "nationale", "national", "comparee", "compares",
    # évolution et discours (410 questions du 08/10 sur les 27 indicateurs vérifiés)
    "evolue", "evoluer", "tendance", "cour", "diminue", "diminuer", "periode", "observer", "observe",
    "observee", "progresse", "progresser", "generale", "general", "variation", "autre", "enregistre", "premier",
    "deuxieme", "troisieme", "quatrieme", "annuelle", "annuel", "degage", "situation", "connu", "connait",
    "connaissent", "forte", "fort", "rapidement", "long", "terme", "importante", "important", "pandemie", "covid",
    "ensemble", "change", "changer", "pourrait", "projetee", "projete", "projection", "comparent", "realise", "chez",
    "permettent", "permet", "pendant", "etaient", "cinq", "deux", "trois", "dix", "douze", "vingt",
    "trente", "quarante", "encore", "amelioration", "ameliore", "davantage", "mesure", "meme", "rythme", "etudiee",
    "revelent", "revele", "matiere", "contre", "point", "devenue", "devenu", "ceux", "celle", "celui", "coutait",
    "coute", "cout", "serie", "fluctuation", "rapport", "partir", "atteint", "recense", "recensement", "kilogramme",
    "precedent", "decennie", "plutot", "estimation", "augmenter", "augmentent", "existe", "cher", "chere",
    "disponibles", "donnees", "statistiques", "debut", "fin",
    # modalités publiées dans les jeux (type de pêche, qualité du riz…) : précisent, ne changent pas le sujet
    "artisanale", "industrielle", "continentale", "maritime", "ordinaire", "brise", "detail", "gro",
}
_GENTILE = re.compile(r"(ais|aise|ien|ienne|ain|aine)s?$")  # « touristes français »
# petits mots de détection de la langue (français et wolof), sans les mots qui disent quoi mesurer
_OUTILS = (_FR | _WO | _WO_FORTS) - {"habitants", "menages", "personnes", "nombre"}
# Mots trop généraux pour dire le sujet d'un indicateur (« Dépenses PUBLIQUES d'éducation » n'est pas la dette
# publique, « INDICE de Gini » se demande aussi « les inégalités »)
_PRECISIONS = {"femme", "homme", "fille", "garcon", "jeune", "age", "rural", "urbain", "rurale", "urbaine", "milieu",
               "elementaire", "primaire", "secondaire", "cycle", "jigeen", "goor", "xale", "personne", "individu"}
# les précisions ne bloquent pas la question (b), mais elles peuvent être le sujet d'un indicateur (« Ensemble garçon »)
_PAS_UN_SUJET = _CADRE | {"indice", "publique", "public", "general", "generale", "national", "nationale", "effectif"}


def _proche(mot: str, vocab) -> bool:
    """Le mot, son pluriel, sa forme collée (« dhabitant ») ou un mot de même racine (6 lettres : « production »
    n'est pas « produits »)."""
    if mot in vocab or forme(mot) in vocab:
        return True
    if len(mot) > 4 and mot[0] in "dl" and _proche(mot[1:], vocab):
        return True
    return len(mot) >= 6 and any(len(v) >= 6 and v[:6] == mot[:6] for v in vocab)


def sujet_dans_la_question(code: str, question: str, precisions: bool = False) -> bool:
    """(a) Le sujet de l'indicateur (deux premiers mots porteurs de son libellé) est dans la question.
    precisions : « garçon », « femmes »… comptent comme sujet (contrôle du choix du LLM : « Ensemble garçon »)."""
    ind = indicateurs().get(code)
    exclus = _PAS_UN_SUJET - _PRECISIONS if precisions else _PAS_UN_SUJET
    sujet = [m for m in mots(ind.libelle_fr.split(" — ")[0])
             if m not in exclus and not m.isdigit() and len(m) > 2][:2] if ind else []
    return not sujet or any(_proche(m, set(index().requete(question))) for m in sujet)


def couvert(code: str, question: str) -> bool:
    """Garde-fou du secours (a) + (b), voir _CADRE."""
    ix = index()
    doc = set(ix.mots_de(code))
    if not sujet_dans_la_question(code, question):
        return False  # (a) « dépenses d'éducation » pour « la dette publique »
    noms_de_zones = {w for z in zones_citees(question) if (zr := zones_ref().get(z))
                     for nom in (zr.libelle_fr, zr.libelle_wo, *zr.variantes) for w in texte_normalise(nom).split()}
    noms_de_zones |= {w for lieu in lieux_inconnus(question) for w in texte_normalise(lieu).split()}  # approchée
    for brut in texte_normalise(question).split():
        if brut in noms_de_zones or resoudre_zone(brut):
            continue
        m = forme(brut)
        if len(m) > 4 and m[0] in "dl" and m[1:] in _SYN:  # « dhabitant »
            m = m[1:]
        if (m in _CADRE or brut in _CADRE or brut in _OUTILS or m.isdigit() or len(m) <= 3 or brut in _MOIS
                or milieu_cite(brut) or _GENTILE.search(brut)):
            continue
        if m not in ix.idf and brut not in ix.idf and m not in _SYN and len(brut) < 6:
            continue  # mot court inconnu du référentiel : faute de frappe, wolof, sigle (« koi », « dagg »)
        if _proche(m, doc) or any(_proche(x, doc) for x in _SYN.get(forme(m), ())):
            continue
        return False  # (b) « président », « électriques », « habitant » (PIB par habitant)
    return True
# « Compare la population de toutes les régions » donnait le seul total du Sénégal (recette du 08/10)
_TOUTES_REGIONS = re.compile(r"\b(toutes les (regions|academies)|chaque (region|academie)|par (region|academie)"
                             r"|les 14 regions|(diiwaan|diwaan) (yepp|yeup|yeppa))\b")
_CLASSEMENT = re.compile(r"\b(le|la|les) (plus|moins)\b|\bquelle region\b|\bclasse(ment)?\b"
                         r"|\b(diiwaan|diwaan|region)\b.*\b(epp|gena|geuna)\b|\bban (region|diiwaan|diwaan)\b"
                         r"|" + _TOUTES_REGIONS.pattern)
_COMPARAISON = re.compile(r"\bcompar|\bentre\b|\bevolution\b|\b(augmente|baisse)\b"
                          r"|\b(yokk|yokku|wanniku|suufe|diggante)\b")  # wolof (KBD) : augmenter, baisser, entre


EGALITE_REGLES = 0.95


def _meme_notion(a, b) -> bool:
    """Deux libellés qui partagent un mot porteur (« retard de croissance ») ; « Production de céréales » et
    « Riz brisé au détail » n'en partagent aucun (08/10 : le prix du riz servi pour sa production)."""
    def porteurs(ind):
        return {m for m in mots(ind.libelle_fr.split(" — ")[0]) if m not in _PAS_UN_SUJET and not m.isdigit()}
    return bool(porteurs(a) & porteurs(b))


def _plus_recent_a_egalite(meilleur: Candidat, candidats: list[Candidat]) -> Candidat:
    """Sans année (0035) : deux indicateurs vérifiés presque à égalité de mots (« Enfants souffrant d'un retard
    de croissance », EDS jusqu'en 2019, et « Prévalence du retard de croissance », EDS jusqu'en 2023) : la série
    qui va le plus loin dans le temps, jamais une projection (FR-020, 08/10)."""
    if meilleur.indicateur.verification != "verifie":
        return meilleur
    proches = [c for c in candidats if c is not meilleur and c.indicateur.verification == "verifie"
               and c.score >= EGALITE_REGLES * meilleur.score and projection(c.indicateur.dataset_id) is None
               and c.indicateur.periode_fin[:4] > meilleur.indicateur.periode_fin[:4]
               and _meme_notion(meilleur.indicateur, c.indicateur)]  # pas le prix du riz pour sa production
    return max(proches, key=lambda c: c.indicateur.periode_fin, default=meilleur)


# Type de mesure demandé (recette du 08/10) : « Taux de scolarisation des filles » n'est pas « Part des filles
# parmi les élèves » (WO-005), « Combien de personnes sont au chômage ? » n'est pas le taux (FR-073, 0024).
_DEMANDE_TAUX = re.compile(r"\b(taux|tolluwaay|tolluwaayu|toluwaay|toluwaayu)\b")
_DEMANDE_EFFECTIF = re.compile(r"\b(combien de (personnes|gens|chomeurs)|nombre de (personnes|chomeurs)|chomeurs"
                               r"|ni amul|nu amul)\b")
PROCHE_DU_MEILLEUR = 0.6  # un candidat aligné sur la mesure demandée passe devant s'il est au moins à 60 %


def _est_taux(c: Candidat) -> bool:
    """Un « taux » au sens du libellé : « Part des filles » est en % sans être le taux de scolarisation."""
    return "taux" in normaliser(c.indicateur.libelle_fr).split()


def _est_effectif(c: Candidat) -> bool:
    x = c.indicateur
    return normaliser(x.unite_affichee or x.unite) in ("personnes", "habitants", "nombre") or \
        normaliser(x.libelle_fr).startswith(("population", "nombre", "effectif"))


def _mesure_alignee(meilleur: Candidat, candidats: list[Candidat], t: str) -> Candidat:
    for demande, est in ((_DEMANDE_EFFECTIF, _est_effectif), (_DEMANDE_TAUX, _est_taux)):
        if demande.search(t) and not est(meilleur):
            alignes = [c for c in candidats if est(c) and c.score >= PROCHE_DU_MEILLEUR * meilleur.score]
            return max(alignes, key=lambda c: c.score, default=meilleur)
    return meilleur


def _couvrant(code: str, candidats: list[Candidat], question: str) -> str | None:
    """Le choix s'il couvre la question ; sinon le suivant qui la couvre (« personnes condamnées » après
    « personnes emprisonnées », « indice de bien-être » après « indice de Gini »), sinon aucun."""
    if couvert(code, question):
        return code
    suivants = sorted((c for c in candidats if c.score >= SEUIL_REGLES and c.indicateur.code != code),
                      key=lambda c: -c.score)
    return next((c.indicateur.code for c in suivants if couvert(c.indicateur.code, question)), None)


def regles(question: str, candidats: list[Candidat], zones: list[str], periodes: list[str],
           precedente: RequeteStructuree | None) -> RequeteStructuree:
    if aucun_mot_connu(question):
        return RequeteStructuree(intention="hors_perimetre", zones=zones, confiance=0.1)
    t = texte_normalise(question)  # « ŋ » et ponctuation collée, comme les candidats
    meilleur = max(candidats, key=lambda c: c.score, default=None)  # le tri par couverture ne compte pas ici
    meilleur = meilleur if meilleur and meilleur.score >= SEUIL_REGLES else None
    if meilleur:
        meilleur = _mesure_alignee(meilleur, candidats, t)
    code = meilleur.indicateur.code if meilleur else None
    if precedente and precedente.indicateur and _suivi(question):
        # « Et pour les femmes ? » : une précision seule garde l'indicateur précédent (avant : la proportion de
        # femmes au gouvernement, recette du 08/10)
        precision_seule = all(m in _CADRE or m in _SUIVI_EN_TETE | _SUIVI_PARTOUT or resoudre_zone(m)
                              for m in mots(question))
        nouveau = bool(code) and not zones and not precision_seule
        # un nouvel indicateur dans un suivi passe aussi le garde-fou : « Et le salaire du président ? » après le
        # chômage donnait le salaire moyen (revue de SAN sur #162)
        code = (_couvrant(code, candidats, question) if nouveau else precedente.indicateur)
        zones = zones or list(precedente.zones)
    elif code and not couvert(code, question):
        code = _couvrant(code, candidats, question)
    elif meilleur and code == meilleur.indicateur.code and not periodes:
        # après le garde-fou : l'équivalent vérifié plus récent, choisi par KBD, peut dire la chose autrement (FR-020)
        code = _plus_recent_a_egalite(meilleur, candidats).indicateur.code
    if code is None:
        return RequeteStructuree(intention="hors_perimetre", zones=zones, confiance=0.3)
    suivi = bool(precedente) and _suivi(question)
    if extremum(question) and len(zones) <= 1:
        intention = "valeur"  # la période du plus haut niveau : la résolution la cherche dans la série
    elif _CLASSEMENT.search(t):
        intention = "classement"
    elif (len(zones) > 1 and not suivi) or len(periodes) > 1 or _COMPARAISON.search(t) or est_evolution(question):
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
