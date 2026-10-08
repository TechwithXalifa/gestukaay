"""Refus : gestion des motifs hors_socle, projection et incompréhension (issue #13).

Principes non négociables :
  1. FR seulement (règle 6, décision 0009) : aucun wolof généré ; le wolof sera écrit par KBD en #25.
  2. Projection : règle générique sans marqueurs ni valeurs en dur —
     année demandée > année en cours (2026) ET année demandée > dernière période publiée de l'indicateur.
     Une année passée non publiée = réponse approchée (#12).
     « demain » ne doit pas devenir une projection (FR-060 est hors socle).
  3. Suggestions : au plus 3 indicateurs proches réellement liés, vérifiés par la résolution
     (zéro chiffre inventé). En mode règles : seuil de score BM25, sinon les 3 phares P1.
     Contre-exemple : « personnes parlent sérère » ne doit jamais suggérer « personnes emprisonnées ».
  4. Message hors_socle : texte du cahier §7.4 mot pour mot :
     « Cette donnée n'existe pas dans les publications de l'ANSD que nous couvrons. »,
     suivi de « Voici des indicateurs proches : » quand des suggestions sont formulées ;
     de « Les chiffres les plus demandés : » quand ce ne sont que les phares (#116, choix KBD).
  5. Incompréhension : drapeau interne incomprehensible dans SortieLLM (pas de changement de contrat) ;
     en règles : aucun mot connu -> incompréhension, requete=None, suggestions=[].
  6. Lieux : lieu déclaré dans rattachements.csv -> #12 ; lieu inconnu (ex. Paris) -> hors_socle.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from gestukaay_contracts.models import (
    Periode,
    RefIndicateur,
    ReponseAucune,
    RequeteStructuree,
    Suggestion,
)
from gestukaay_socle.indicateurs import Indicateur, indicateurs
from gestukaay_socle.zones import normaliser, zones

from .approchee import rattachements
from .candidats import periodes_citees
from .comprehension import Comprise
from .resolution import ANNEE_EN_COURS, Resolution, resoudre
from .socle import Socle

SEUIL_SUGGESTIONS = 6.0
INDICATEURS_PHARES_P1 = ("pvswjnd", "dwibrlf", "jcvcajc.taux-de-pauvrete")

MESSAGE_HORS_SOCLE_BASE = "Cette donnée n'existe pas dans les publications de l'ANSD que nous couvrons."
MESSAGE_HORS_SOCLE_SUGGESTIONS = (
    "Cette donnée n'existe pas dans les publications de l'ANSD que nous couvrons. "
    "Voici des indicateurs proches :"
)
MESSAGE_HORS_SOCLE_PHARES = (
    "Cette donnée n'existe pas dans les publications de l'ANSD que nous couvrons. "
    "Les chiffres les plus demandés :"
)
MESSAGE_PROJECTION = (
    "Gëstukaay ne fait pas de prévisions. "
    "Les projections officielles sont publiées par l'ANSD sur www.ansd.sn."
)
MESSAGE_PROJECTION_POPULATION = (
    "Gëstukaay ne fait pas de prévisions. "
    "Les projections officielles de population sont publiées par l'ANSD sur www.ansd.sn."
)
MESSAGE_INCOMPREHENSION = "Je n'ai pas bien compris. Essayez par exemple : « Combien d'habitants à Thiès ? »"


@dataclass(frozen=True)
class Refus:
    motif: Literal["hors_socle", "projection", "incomprehension", "non_disponible"]
    message: str
    suggestions: list[Suggestion]
    requete: RequeteStructuree | None = None


def _lieu_phrase(zone_code: str) -> str:
    if not zone_code or zone_code == "SN":
        return "au Sénégal"
    z = zones().get(zone_code)
    if not z:
        return "au Sénégal"
    if z.niveau == "region":
        return f"dans la région de {z.libelle_fr}"
    if z.niveau == "departement":
        return f"dans le département de {z.libelle_fr}"
    if z.niveau == "academie":
        return f"dans l'académie de {z.libelle_fr}"
    return f"à {z.libelle_fr}"


def formuler_question_suggeree(ind: Indicateur, zone_code: str = "SN") -> str:
    """Formule une question naturelle en français pour un indicateur suggéré."""
    code = ind.code
    lieu = _lieu_phrase(zone_code)

    if code == "pvswjnd":
        return f"Combien d'habitants {lieu} ?"
    if code == "dwibrlf":
        return f"Quel est le taux de chômage {lieu} ?"
    if "taux-de-pauvrete" in code:
        return f"Quel est le taux de pauvreté {lieu} ?"
    if "gini" in code:
        return f"Quel est l'indice de Gini {lieu} ?"
    if "inflation" in normaliser(ind.libelle_fr) or code == "tsghpfc.indice-global":
        return f"Quelle est l'inflation {lieu} ?"
    if "salaire" in normaliser(ind.libelle_fr):
        return f"Quel est le salaire moyen {lieu} ?"
    if "scolarisation" in normaliser(ind.libelle_fr):
        return f"Quel est le taux de scolarisation {lieu} ?"
    if "alphabetisation" in normaliser(ind.libelle_fr):
        return f"Quel est le taux d'alphabétisation {lieu} ?"
    if "menage" in normaliser(ind.libelle_fr) and "taille" in normaliser(ind.libelle_fr):
        return f"Quelle est la taille moyenne des ménages {lieu} ?"
    if "esperance-de-vie" in code or "esperance" in normaliser(ind.libelle_fr):
        return f"Quelle est l'espérance de vie {lieu} ?"
    if "electricite" in normaliser(ind.libelle_fr) or "eclairage" in normaliser(ind.libelle_fr):
        return f"Quel est le taux d'accès à l'électricité {lieu} ?"

    lib = ind.libelle_fr
    if " — " in lib:
        lib = lib.split(" — ")[0].strip()

    lib_norm = normaliser(lib)
    if lib_norm.startswith(("taux", "indice", "nombre", "prix", "pourcentage", "quotient", "salaire", "parc")):
        return f"Quel est le {lib} {lieu} ?"
    if lib_norm.startswith(("part", "proportion", "esperance", "taille", "quantite", "production")):
        return f"Quelle est la {lib} {lieu} ?"
    return f"Quel est le chiffre pour {lib} {lieu} ?"


def verifier_suggestion(
    socle: Socle,
    ind_code: str,
    zone: str = "SN",
) -> Suggestion | None:
    """Vérifie qu'un indicateur proposé est réellement résolu dans le socle (zéro chiffre inventé)."""
    ind = indicateurs().get(ind_code)
    if not ind:
        return None

    z_test = zone if (zone != "SN" and zones().get(zone)) else "SN"
    req = RequeteStructuree(
        intention="valeur",
        indicateur=ind_code,
        zones=[z_test],
        periode=Periode(type="derniere"),
        confiance=1.0,
    )
    res = resoudre(socle, req)
    if not (isinstance(res, Resolution) and res.resultats):
        if z_test != "SN":
            req_sn = RequeteStructuree(
                intention="valeur",
                indicateur=ind_code,
                zones=["SN"],
                periode=Periode(type="derniere"),
                confiance=1.0,
            )
            res_sn = resoudre(socle, req_sn)
            if isinstance(res_sn, Resolution) and res_sn.resultats:
                z_test = "SN"
            else:
                return None
        else:
            return None

    ref_ind = RefIndicateur(code=ind.code, libelle=ind.libelle_fr)
    return Suggestion(
        indicateur=ref_ind,
        question_suggeree=formuler_question_suggeree(ind, z_test),
    )


def obtenir_suggestions(
    socle: Socle,
    comprise: Comprise,
    zone: str = "SN",
) -> list[Suggestion]:
    """Obtient au plus 3 suggestions d'indicateurs vérifiées par la résolution.

    Règles :
      - Si comprise.proches existe (via LLM ou candidats au-dessus du seuil) : les tester en priorité ;
      - Sinon (ou en complément) : repli sur les 3 indicateurs phares P1 ;
      - Chaque suggestion doit être résolue avec succès dans le socle (zéro chiffre inventé) ;
      - Déduplication par code indicateur.
    """
    suggestions: list[Suggestion] = []
    codes_vus: set[str] = set()

    # 1. Candidats proches identifiés
    for cand in comprise.proches:
        code = cand.indicateur.code
        if code not in codes_vus:
            sugg = verifier_suggestion(socle, code, zone)
            if sugg:
                codes_vus.add(code)
                suggestions.append(sugg)
            if len(suggestions) == 3:
                return suggestions

    # 2. Repli sur les 3 phares P1 si nécessaire
    for code_p1 in INDICATEURS_PHARES_P1:
        if code_p1 not in codes_vus:
            sugg = verifier_suggestion(socle, code_p1, zone)
            if sugg:
                codes_vus.add(code_p1)
                suggestions.append(sugg)
            if len(suggestions) == 3:
                break

    return suggestions


def message_hors_socle(comprise: Comprise, suggestions: list[Suggestion]) -> str:
    """Les phares seuls ne sont pas présentés comme « proches » : ils n'ont pas de lien avec la question."""
    if not suggestions:
        return MESSAGE_HORS_SOCLE_BASE
    proches = {c.indicateur.code for c in comprise.proches}
    if any(s.indicateur.code in proches for s in suggestions):
        return MESSAGE_HORS_SOCLE_SUGGESTIONS
    return MESSAGE_HORS_SOCLE_PHARES


def annee_demandee(requete: RequeteStructuree, question: str = "") -> int | None:
    """Extrait l'année numérique demandée soit depuis la période, soit depuis le texte."""
    if requete.periode and requete.periode.valeur:
        m = re.search(r"\b(19|20)\d\d\b", requete.periode.valeur)
        if m:
            return int(m.group(0))
    if question:
        for p in periodes_citees(question):
            m = re.search(r"\b(19|20)\d\d\b", p)
            if m:
                return int(m.group(0))
    return None


def derniere_annee_publiee(socle: Socle, code_indicateur: str) -> int | None:
    """Trouve la dernière année publiée pour un indicateur dans le socle."""
    annees = []
    for o in socle.observations(code_indicateur):
        m = re.search(r"\b(19|20)\d\d\b", o.periode)
        if m:
            annees.append(int(m.group(0)))
    if annees:
        return max(annees)
    ind = indicateurs().get(code_indicateur)
    if ind and ind.periode_fin:
        m = re.search(r"\b(19|20)\d\d\b", ind.periode_fin)
        if m:
            return int(m.group(0))
    return None


def est_projection(
    socle: Socle,
    requete: RequeteStructuree,
    question: str = "",
    annee_en_cours: int = ANNEE_EN_COURS,
) -> tuple[bool, int | None]:
    """Détermine si la demande concerne une projection non publiée.

    Règle générique :
      - année demandée > année en cours (2026) ET année demandée > dernière période publiée de l'indicateur.
      - une année passée non publiée relève de la réponse approchée (#12).
      - « demain » ou des questions sans année ne deviennent pas des projections (FR-060 est hors socle).
    """
    if not requete.indicateur:
        return False, None
    annee = annee_demandee(requete, question)
    if annee is None:
        return False, None
    derniere = derniere_annee_publiee(socle, requete.indicateur)
    if derniere is None:
        return annee > annee_en_cours, annee
    if annee > annee_en_cours and annee > derniere:
        return True, annee
    return False, annee


def refuser(
    socle: Socle,
    comprise: Comprise,
    question: str = "",
    langue: str = "fr",
) -> Refus:
    """Construit un refus (motif, message, suggestions vérifiées) selon les règles du cahier."""
    # -------------------------------------------------------------------
    # 1. Incompréhension : question inintelligible ou aucun mot connu
    # -------------------------------------------------------------------
    if comprise.incomprehensible:
        return Refus(
            motif="incomprehension",
            message=MESSAGE_INCOMPREHENSION,
            suggestions=[],
            requete=None,
        )

    # -------------------------------------------------------------------
    # 2. Lieu inconnu non rattaché (ex. Paris) -> hors_socle
    # -------------------------------------------------------------------
    rats = rattachements()
    for lieu in comprise.lieux_inconnus:
        if normaliser(lieu) not in rats:
            # Lieu inconnu non déclaré dans rattachements.csv (ex. Paris)
            suggs = obtenir_suggestions(socle, comprise, "SN")
            msg = message_hors_socle(comprise, suggs)
            return Refus(
                motif="hors_socle",
                message=msg,
                suggestions=suggs,
                requete=comprise.requete,
            )

    # -------------------------------------------------------------------
    # 3. Projection non publiée
    # -------------------------------------------------------------------
    est_proj, _ = est_projection(socle, comprise.requete, question)
    if est_proj and comprise.requete.indicateur:
        ind = indicateurs().get(comprise.requete.indicateur)
        is_pop = ind and "population" in normaliser(ind.libelle_fr)
        msg = MESSAGE_PROJECTION_POPULATION if is_pop else MESSAGE_PROJECTION
        sugg = verifier_suggestion(socle, comprise.requete.indicateur, "SN")
        suggs = [sugg] if sugg else []
        return Refus(
            motif="projection",
            message=msg,
            suggestions=suggs,
            requete=comprise.requete,
        )

    # -------------------------------------------------------------------
    # 4. Hors socle : question sans indicateur, hors périmètre ou non publiée
    # -------------------------------------------------------------------
    zone_dem = comprise.requete.zones[0] if comprise.requete.zones else "SN"
    suggs = obtenir_suggestions(socle, comprise, zone_dem)
    msg = message_hors_socle(comprise, suggs)
    return Refus(
        motif="hors_socle",
        message=msg,
        suggestions=suggs,
        requete=comprise.requete,
    )


def construire_reponse_aucune(
    refus: Refus,
    question: str,
    version_socle: str = "2026.10.0",
    id_reponse: str | None = None,
    url: str | None = None,
    langue: str = "fr",
    transcription: str | None = None,
    latence_ms: int | None = None,
) -> ReponseAucune:
    """Instancie le modèle ReponseAucune du contrat d'échange."""
    ident = id_reponse or f"refus-{uuid.uuid4().hex[:8]}"
    return ReponseAucune(
        id=ident,
        url=url or f"https://app.gestukaay.test/r/{ident}",
        question=question,
        langue="fr",  # FR seulement (règle 6, décision 0009)
        transcription=transcription,
        requete=refus.requete,
        version_socle=version_socle,
        cree_le=datetime.now(UTC),
        latence_ms=latence_ms,
        issue="aucune",
        motif=refus.motif,
        message=refus.message,
        suggestions=refus.suggestions,
    )
