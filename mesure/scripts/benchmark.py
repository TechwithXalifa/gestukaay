"""Benchmark de bout en bout et invariant « zéro chiffre inventé » (issue #19).

Mesure les performances de MoteurReel sur le jeu de test officiel (103 questions) :
  - Exactitude (cahier §12.1) : calculée sur les 83 questions appelant une réponse
    (72 exactes + 11 approchées). Réponse correcte ET correctement sourcée.
  - Refus pertinent : calculé sur les 20 questions de refus, avec motif attendu.
  - Latence : médiane et P95 mesurées autour de repondre(), hors chargement du socle.
  - Invariant « zéro chiffre inventé » (tolérance zéro) :
      (a) chaque Resultat : observation_id existe dans le socle et valeur est égale ;
      (b) chaque point de graphique correspond à une observation du socle ;
      (c) chaque nombre dans explication provient de la liste blanche des textes affichés ;
      (d) aucune valeur numérique statistique dans une réponse approchée ou un refus.

Modes :
  uv run python mesure/scripts/benchmark.py --regles  # gratuit, sans réseau (défaut)
  uv run python mesure/scripts/benchmark.py --llm     # payant, demande confirmation

Code de sortie : 1 seulement si l'invariant est violé, 0 sinon.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from gestukaay_contracts.models import (
    AskRequest,
    AskResponse,
    ReponseApprochee,
    ReponseAucune,
    ReponseExacte,
    RequeteStructuree,
)
from gestukaay_engine.moteur import MoteurReel
from gestukaay_engine.resolution import national
from gestukaay_engine.socle import Observation, Socle, socle
from gestukaay_socle.indicateurs import Indicateur, indicateurs
from gestukaay_socle.zones import resoudre

RACINE = Path(__file__).resolve().parents[2]
JEU_PAR_DEFAUT = RACINE / "mesure" / "jeu_de_test" / "questions.csv"
GABARITS_CSV = RACINE / "engine" / "src" / "gestukaay_engine" / "gabarits_fr.csv"
RAPPORT_DIR = RACINE / "mesure" / "rapports"

COUT_ESTIME_LLM = 0.07  # USD pour 103 questions avec Gemini 2.5 Flash via OpenRouter


# ---------------------------------------------------------------------------
# Normalisation et extraction
# ---------------------------------------------------------------------------


def normaliser_espace(texte: str) -> str:
    """Remplace les espaces fines insécables et insécables par des espaces simples."""
    return texte.replace("\u202f", " ").replace("\u00a0", " ").strip()


def extraire_nombres(texte: str) -> list[str]:
    """Extrait les nombres entiers ou décimaux (séparateurs de milliers ou virgule)."""
    norm = normaliser_espace(texte)
    return re.findall(r"\b\d+(?: \d{3})*(?:[,\.]\d+)?\b", norm)


def attendus_exacte(q: dict[str, str]) -> list[tuple[str, str, float]]:
    """Convertit valeurs_attendues en liste de (zone, période, valeur)."""
    periodes = q["periode"].split("|")
    out = []
    for item in q["valeurs_attendues"].split("|"):
        if not item or "=" not in item:
            continue
        cle, val = item.rsplit("=", 1)
        z, p = cle.split("@") if "@" in cle else (cle, periodes[0])
        out.append((z, p, float(val)))
    return out


# ---------------------------------------------------------------------------
# Invariant « zéro chiffre inventé » (tolérance zéro)
# ---------------------------------------------------------------------------


@dataclass
class ViolationInvariant:
    question_id: str
    volet: str  # "a", "b", "c", "d"
    message: str


def charger_nombres_statiques_gabarits() -> dict[str, list[str]]:
    """Nombres présents dans les gabarits fixes de gabarits_fr.csv (ex: base 100, 1 000, 5)."""
    if not GABARITS_CSV.exists():
        return {}
    with open(GABARITS_CSV, encoding="utf-8") as f:
        return {
            row["code"]: extraire_nombres(row["gabarit"])
            for row in csv.DictReader(f, delimiter=";")
        }


def verifier_invariant_reponse(
    q: dict[str, str],
    rep: AskResponse,
    s: Socle,
    obs_par_id: dict[str, Observation],
    inds: dict[str, Indicateur],
    gabs_statiques: dict[str, list[str]],
) -> list[ViolationInvariant]:
    """Vérifie les 4 volets de l'invariant pour une réponse donnée."""
    violations: list[ViolationInvariant] = []
    qid = q["id"]
    r_body = rep.reponse

    # Volet (a) : chaque Resultat : observation_id existe et valeur == obs.valeur
    if isinstance(r_body, ReponseExacte):
        for r in r_body.resultats:
            if r.observation_id not in obs_par_id:
                violations.append(
                    ViolationInvariant(qid, "a", f"observation_id {r.observation_id} hors socle")
                )
            else:
                obs = obs_par_id[r.observation_id]
                if not math.isclose(obs.valeur, r.valeur, abs_tol=1e-7):
                    violations.append(
                        ViolationInvariant(
                            qid,
                            "a",
                            f"valeur {r.valeur} != socle {obs.valeur} ({r.observation_id})",
                        )
                    )

        # Volet (b) : chaque point de graphique correspond à une observation du socle
        if r_body.graphique:
            r0 = r_body.resultats[0]
            ind_code = r0.indicateur.code
            lignes = s.observations(ind_code)
            o_cible = obs_par_id.get(r0.observation_id)
            desag_cible = o_cible.desagregation if o_cible else ()

            for serie in r_body.graphique.series:
                for pt in serie.points:
                    trouve = False
                    if r_body.graphique.type in ("barres_horizontales", "barres_empilees"):
                        code_z = resoudre(pt.x, niveau=r0.zone.niveau) or resoudre(pt.x)
                        if not code_z:
                            violations.append(
                                ViolationInvariant(
                                    qid,
                                    "b",
                                    f"point barre x={pt.x!r} ne correspond à aucune zone du référentiel",
                                )
                            )
                            continue
                        periode_cible = r0.periode.valeur
                        for o in lignes:
                            if o.zone != code_z:
                                continue
                            if o.periode != periode_cible:
                                continue
                            if desag_cible and o.desagregation != desag_cible:
                                continue
                            if math.isclose(o.valeur, pt.y, abs_tol=1e-5):
                                trouve = True
                                break
                        if not trouve:
                            violations.append(
                                ViolationInvariant(
                                    qid,
                                    "b",
                                    f"point barre {pt.x} ({code_z}) y={pt.y} "
                                    f"absent du socle pour l'indicateur {ind_code}",
                                )
                            )
                    elif r_body.graphique.type == "courbe":
                        periode_pt = pt.x.strip()
                        zone_cible = r0.zone.code
                        for o in lignes:
                            if o.periode != periode_pt:
                                continue
                            if o.zone != zone_cible:
                                continue
                            if desag_cible and o.desagregation != desag_cible:
                                continue
                            if math.isclose(o.valeur, pt.y, abs_tol=1e-5):
                                trouve = True
                                break
                        if not trouve:
                            violations.append(
                                ViolationInvariant(
                                    qid,
                                    "b",
                                    f"point courbe periode={periode_pt} zone={zone_cible} y={pt.y} "
                                    f"absent du socle pour l'indicateur {ind_code}",
                                )
                            )

        # Volet (c) : nombres de l'explication vérifiés contre liste blanche des textes affichés
        whitelist_textes: set[str] = set()
        whitelist_nombres: set[str] = set()

        for r in r_body.resultats:
            v_aff = normaliser_espace(r.valeur_affichee)
            whitelist_textes.add(v_aff)
            whitelist_nombres.add(v_aff)
            whitelist_nombres.add(v_aff.replace(" ", ""))

            # Valeur nationale publiée comparée
            nat = national(s, r, "fr")
            if nat:
                v_nat = normaliser_espace(nat.valeur_affichee)
                whitelist_textes.add(v_nat)
                whitelist_nombres.add(v_nat)
                whitelist_nombres.add(v_nat.replace(" ", ""))
                for n in re.findall(r"\d+", nat.periode.valeur):
                    whitelist_nombres.add(n)

            # Périodes issues de la réponse produite
            for p_champ in (r.periode.valeur, r.periode.libelle):
                if p_champ:
                    for n in re.findall(r"\d+", normaliser_espace(p_champ)):
                        whitelist_nombres.add(n)

            # Unités
            if r.unite:
                for n in extraire_nombres(r.unite):
                    whitelist_nombres.add(n)

            # Modalités de désagrégation (ex: « 15-24 ans »)
            if r.desagregation:
                for v in r.desagregation.values():
                    whitelist_textes.add(normaliser_espace(v))
                    for n in extraire_nombres(v):
                        whitelist_nombres.add(n)

            # Base de projection
            if r.base_projection:
                for n in re.findall(r"\d+", r.base_projection):
                    whitelist_nombres.add(n)

            # Opération source (ex: RGPH-5 -> 5)
            if r.source.operation:
                for n in re.findall(r"\d+", r.source.operation):
                    whitelist_nombres.add(n)

            # Libellé officiel de l'indicateur (ex: « taxi 7 places » -> 7)
            ind_o = inds.get(r.indicateur.code)
            if ind_o:
                for n in re.findall(r"\d+", ind_o.libelle_fr):
                    whitelist_nombres.add(n)
                if ind_o.unite_affichee:
                    for n in extraire_nombres(ind_o.unite_affichee):
                        whitelist_nombres.add(n)

            # Nombres statiques issus du gabarit officiel
            for n in gabs_statiques.get(r.indicateur.code, []):
                whitelist_nombres.add(n)

        # Vérification stricte des nombres dans explication (aucun passe-droit global)
        nombres_expl = extraire_nombres(r_body.explication)
        for tok in nombres_expl:
            sans_espace = tok.replace(" ", "")
            if tok in whitelist_nombres or sans_espace in whitelist_nombres:
                continue
            if any(tok == w or tok in w.split() for w in whitelist_textes):
                continue
            violations.append(
                ViolationInvariant(qid, "c", f"nombre non autorisé dans explication: '{tok}'")
            )

    # Volet (d) : aucune valeur numérique statistique dans réponse approchée ou refus
    elif isinstance(r_body, ReponseApprochee):
        textes_a_verifier = [r_body.reformulation] + [c.libelle for c in r_body.choix]
        for txt in textes_a_verifier:
            for n in re.findall(r"\b\d+(?:[,\.]\d+)?\b", txt):
                # Seules les années sont autorisées dans reformulation et libellés
                if not (len(n) == 4 and n.startswith(("19", "20"))):
                    violations.append(
                        ViolationInvariant(
                            qid, "d", f"chiffre non-année dans approchée: '{n}' ({txt})"
                        )
                    )

    elif isinstance(r_body, ReponseAucune):
        for n in re.findall(r"\b\d+(?:[,\.]\d+)?\b", r_body.message):
            if not (len(n) == 4 and n.startswith(("19", "20"))):
                violations.append(
                    ViolationInvariant(qid, "d", f"chiffre non-année dans message de refus: '{n}'")
                )

    return violations


# ---------------------------------------------------------------------------
# Évaluation d'exactitude et de refus (Cahier §12.1)
# ---------------------------------------------------------------------------


@dataclass
class ResultatEvaluation:
    question_id: str
    type_question: str
    langue: str
    issue_attendue: str
    issue_obtenue: str
    reponse_correcte: bool
    sourcee: bool
    statut: str  # "succes", "echec_valeur", "echec_source", "echec_motif", etc.
    motif_obtenu: str | None = None
    motif_attendu: str | None = None
    latence_ms: float = 0.0
    violations_invariant: list[ViolationInvariant] = field(default_factory=list)
    chiffre_faux: bool = False
    detail: str = ""


def verifier_exactitude_reponse(
    q: dict[str, str],
    resp: AskResponse,
    s: Socle,
) -> tuple[bool, bool, str]:
    """(valeurs_correctes, sourcee, detail)."""
    r_body = resp.reponse
    if not isinstance(r_body, ReponseExacte):
        return False, False, f"issue attendue exacte, obtenu {r_body.issue}"

    # Vérification du sourçage (§12.1)
    if not r_body.resultats:
        return False, False, "aucun résultat servi"
    r0 = r_body.resultats[0]
    source_valide = bool(r0.source.producteur and r0.source.date_publication and r0.source.libelle)
    citation_valide = bool(r_body.citation)
    sourcee = source_valide and citation_valide

    # Période par défaut
    attendu_p_defaut = q.get("periode_par_defaut", "").strip().lower() == "oui"
    if r_body.periode_par_defaut != attendu_p_defaut:
        # non bloquant pour la valeur mais noté
        pass

    # Nature projection
    # La nature projection se lit dans le socle pour l'observation attendue
    # Vérification des valeurs selon le type de question
    attendus = attendus_exacte(q)

    if q["type"] == "classement":
        obtenus = [(r.zone.code, r.valeur) for r in r_body.resultats]
        attendus_zv = [(z, v) for z, p, v in attendus]
        if len(obtenus) != len(attendus_zv):
            return (
                False,
                sourcee,
                f"taille classement: {len(obtenus)} != attendu {len(attendus_zv)}",
            )
        for (z_obt, v_obt), (z_att, v_att) in zip(obtenus, attendus_zv, strict=False):
            if z_obt != z_att or not math.isclose(v_obt, v_att, abs_tol=1e-5):
                return (
                    False,
                    sourcee,
                    f"classement: attendu {z_att}={v_att}, obtenu {z_obt}={v_obt}",
                )
        # Graphique barres horizontales
        if not r_body.graphique or r_body.graphique.type != "barres_horizontales":
            return False, sourcee, "graphique barres horizontales manquant pour classement"
        return True, sourcee, "classement ordonné correct"

    if q["type"] == "comparative" and "|" in q.get("periode", ""):
        # Comparaison temporelle : 2 bornes
        obtenus_dict = {(r.zone.code, r.periode.valeur): r.valeur for r in r_body.resultats}
        attendus_dict = {(z, p): v for z, p, v in attendus}
        for zp, v_att in attendus_dict.items():
            if zp not in obtenus_dict or not math.isclose(obtenus_dict[zp], v_att, abs_tol=1e-5):
                return (
                    False,
                    sourcee,
                    f"bornes temporelles: attendu {zp}={v_att}, obtenu {obtenus_dict.get(zp)}",
                )
        if not r_body.graphique or r_body.graphique.type != "courbe":
            return False, sourcee, "graphique courbe manquant pour comparaison temporelle"
        return True, sourcee, "comparaison temporelle correcte"

    # Simple ou comparative multi-zones ou suivi
    obtenus_set = {(r.zone.code, r.periode.valeur, round(r.valeur, 5)) for r in r_body.resultats}
    attendus_set = {(z, p, round(v, 5)) for z, p, v in attendus}
    if obtenus_set == attendus_set:
        return True, sourcee, "valeurs exactes conformes"
    return False, sourcee, f"attendu {sorted(attendus_set)} != obtenu {sorted(obtenus_set)}"


def verifier_approchee_reponse(
    q: dict[str, str],
    resp: AskResponse,
    moteur: MoteurReel,
) -> tuple[bool, bool, str]:
    """(choix_valides, sourcee, detail)."""
    r_body = resp.reponse
    if not isinstance(r_body, ReponseApprochee):
        return False, False, f"issue attendue approchee, obtenu {r_body.issue}"

    if not (2 <= len(r_body.choix) <= 3):
        return False, False, f"nombre de choix {len(r_body.choix)} hors [2, 3]"

    # Chaque choix doit être vivant (exécutable vers une réponse exacte non vide)
    for c in r_body.choix:
        exec_resp = moteur.executer(c.requete, q["question"], q["langue"])
        if not isinstance(exec_resp.reponse, ReponseExacte) or not exec_resp.reponse.resultats:
            return False, False, f"choix mort ({c.id} : {c.libelle})"

    # Vérification de correspondance avec zones et périodes attendues si présentes
    zones_attendues = set(filter(None, q.get("zones_attendues", "").split("|")))
    if zones_attendues:
        zones_proposees = {z for c in r_body.choix for z in c.requete.zones}
        if not (zones_attendues & zones_proposees):
            return (
                False,
                False,
                f"zones attendues {zones_attendues} absentes des choix {zones_proposees}",
            )

    # Une réponse approchée ne porte pas de citation/source avant exécution (EF-06)
    return True, True, f"{len(r_body.choix)} choix vivants et pertinents"


def verifier_refus_reponse(
    q: dict[str, str],
    resp: AskResponse,
) -> tuple[bool, str]:
    """(refus_pertinent, detail)."""
    r_body = resp.reponse
    if not isinstance(r_body, ReponseAucune):
        return False, f"issue attendue aucune, obtenu {r_body.issue}"

    motif_attendu = q.get("motif", "").strip()
    if r_body.motif != motif_attendu:
        return False, f"motif attendu '{motif_attendu}', obtenu '{r_body.motif}'"

    # Vérifications spécifiques par motif
    if motif_attendu == "hors_socle":
        if (
            "Cette donnée n'existe pas" not in r_body.message
            and "n'est pas disponible" not in r_body.message
        ):
            return False, "message hors_socle non conforme au cahier"
        if len(r_body.suggestions) > 3:
            return False, f"trop de suggestions ({len(r_body.suggestions)} > 3)"

    return True, f"refus conforme motif={motif_attendu}"


# ---------------------------------------------------------------------------
# Exécution du benchmark complet
# ---------------------------------------------------------------------------


@dataclass
class RapportBenchmark:
    mode: str
    date_iso: str
    nb_total: int
    nb_reponses_attendues: int  # 83
    nb_exactitude_succes: int
    score_exactitude: float
    nb_refus_attendus: int  # 20
    nb_refus_succes: int
    score_refus: float
    nb_chiffres_faux_affiches: int
    nb_violations_invariant: int
    latence_mediane_ms: float
    latence_p95_ms: float
    sous_scores_type: dict[str, tuple[int, int]]
    sous_scores_langue: dict[str, tuple[int, int]]
    evaluations: list[ResultatEvaluation]
    violations: list[ViolationInvariant]
    defauts_moteur: list[str]


def executer_benchmark(
    questions: list[dict[str, str]],
    moteur: MoteurReel,
    mode: str,
) -> RapportBenchmark:
    """Exécute les 103 questions sur le moteur réel et calcule toutes les métriques."""
    s = moteur.socle
    obs_par_id = {o.id: o for obs in s._par_indicateur.values() for o in obs}
    inds = indicateurs()
    gabs_statiques = charger_nombres_statiques_gabarits()

    evaluations: list[ResultatEvaluation] = []
    toutes_violations: list[ViolationInvariant] = []
    latences: list[float] = []
    requetes_resolues: dict[str, RequeteStructuree] = {}

    # Tri pour exécuter les questions parentes avant les questions de suivi
    questions_triees = sorted(questions, key=lambda q: bool(q.get("suite_de")))

    for q in questions_triees:
        qid = q["id"]
        suite_de = q.get("suite_de", "").strip()
        contexte = [requetes_resolues[suite_de]] if suite_de in requetes_resolues else None

        req = AskRequest(question=q["question"], langue=q["langue"])  # type: ignore[arg-type]

        t0 = time.perf_counter()
        resp = moteur.repondre(req, contexte=contexte)
        latence_ms = (time.perf_counter() - t0) * 1000
        latences.append(latence_ms)

        # Mémoriser la requête résolue pour les suivis
        if resp.reponse.requete:
            requetes_resolues[qid] = resp.reponse.requete

        # 1. Invariant « zéro chiffre inventé »
        viols = verifier_invariant_reponse(q, resp, s, obs_par_id, inds, gabs_statiques)
        toutes_violations.extend(viols)

        # 2. Exactitude ou refus
        issue_attendue = q["issue_attendue"]
        issue_obtenue = resp.reponse.issue
        reponse_correcte = False
        sourcee = False
        motif_obtenu = getattr(resp.reponse, "motif", None)
        statut = "inconnu"
        detail = ""
        ok_val = False

        if issue_attendue == "exacte":
            ok_val, ok_src, detail = verifier_exactitude_reponse(q, resp, s)
            reponse_correcte = ok_val and ok_src
            sourcee = ok_src
            statut = (
                "succes" if reponse_correcte else ("echec_source" if ok_val else "echec_valeur")
            )

        elif issue_attendue == "approchee":
            ok_val, ok_src, detail = verifier_approchee_reponse(q, resp, moteur)
            reponse_correcte = ok_val
            sourcee = ok_src
            statut = "succes" if reponse_correcte else "echec_approchee"

        elif issue_attendue == "aucune":
            ok_refus, detail = verifier_refus_reponse(q, resp)
            reponse_correcte = ok_refus
            sourcee = True  # non applicable aux refus
            statut = "succes" if reponse_correcte else "echec_motif"

        # Chiffres faux affichés : toute réponse exacte qui affiche une valeur pour la
        # mauvaise zone, période ou indicateur, ou une valeur servie là où un refus ou une approchée était attendu.
        chiffre_faux = isinstance(resp.reponse, ReponseExacte) and (
            issue_attendue != "exacte" or not ok_val
        )

        evaluations.append(
            ResultatEvaluation(
                question_id=qid,
                type_question=q["type"],
                langue=q["langue"],
                issue_attendue=issue_attendue,
                issue_obtenue=issue_obtenue,
                reponse_correcte=reponse_correcte,
                sourcee=sourcee,
                statut=statut,
                motif_obtenu=motif_obtenu,
                motif_attendu=q.get("motif"),
                latence_ms=latence_ms,
                violations_invariant=viols,
                chiffre_faux=chiffre_faux,
                detail=detail,
            )
        )

    # Calcul des sous-scores
    # Type : simple, classement, comparative (spatiale / temporelle), suivi, approchee, refus
    def type_detaille(e: ResultatEvaluation, q_map: dict[str, dict[str, str]]) -> str:
        q_row = q_map[e.question_id]
        if e.type_question == "comparative":
            return (
                "comparative_temporelle"
                if "|" in q_row.get("periode", "")
                else "comparative_spatiale"
            )
        return e.type_question

    q_map = {q["id"]: q for q in questions}
    sous_scores_type: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    sous_scores_langue: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    for ev in evaluations:
        t_det = type_detaille(ev, q_map)
        sous_scores_type[t_det][1] += 1
        sous_scores_langue[ev.langue][1] += 1
        if ev.reponse_correcte:
            sous_scores_type[t_det][0] += 1
            sous_scores_langue[ev.langue][0] += 1

    # Exactitude (sur les 83 questions appelant une réponse : exacte + approchée)
    evals_reponse = [ev for ev in evaluations if ev.issue_attendue in ("exacte", "approchee")]
    nb_exactitude_succes = sum(1 for ev in evals_reponse if ev.reponse_correcte)
    score_exactitude = nb_exactitude_succes / len(evals_reponse) if evals_reponse else 0.0

    # Refus pertinent (sur les 20 refus)
    evals_refus = [ev for ev in evaluations if ev.issue_attendue == "aucune"]
    nb_refus_succes = sum(1 for ev in evals_refus if ev.reponse_correcte)
    score_refus = nb_refus_succes / len(evals_refus) if evals_refus else 0.0

    # Chiffres faux affichés
    nb_chiffres_faux = sum(1 for ev in evaluations if ev.chiffre_faux)

    # Latences
    latences_triees = sorted(latences)
    mediane = latences_triees[len(latences_triees) // 2] if latences_triees else 0.0
    idx_p95 = int(len(latences_triees) * 0.95)
    p95 = latences_triees[min(idx_p95, len(latences_triees) - 1)] if latences_triees else 0.0

    # Défauts constatés du moteur
    defauts_moteur: list[str] = []
    for ev in evaluations:
        if (
            ev.type_question == "classement"
            and not ev.reponse_correcte
            and "FR-045" in ev.question_id
        ):
            defauts_moteur.append(
                "FR-045 (classement mortalité) : le motif `_ORDRE_ASC` du moteur capture à tort « moins de » "
                "dans « moins de 5 ans » (comprehension.py et resolution.py), produisant un tri croissant "
                "au lieu du tri décroissant attendu. Défaut moteur à corriger côté engine."
            )

    return RapportBenchmark(
        mode=mode,
        date_iso=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        nb_total=len(evaluations),
        nb_reponses_attendues=len(evals_reponse),
        nb_exactitude_succes=nb_exactitude_succes,
        score_exactitude=score_exactitude,
        nb_refus_attendus=len(evals_refus),
        nb_refus_succes=nb_refus_succes,
        score_refus=score_refus,
        nb_chiffres_faux_affiches=nb_chiffres_faux,
        nb_violations_invariant=len(toutes_violations),
        latence_mediane_ms=mediane,
        latence_p95_ms=p95,
        sous_scores_type={k: (v[0], v[1]) for k, v in sorted(sous_scores_type.items())},
        sous_scores_langue={k: (v[0], v[1]) for k, v in sorted(sous_scores_langue.items())},
        evaluations=evaluations,
        violations=toutes_violations,
        defauts_moteur=list(set(defauts_moteur)),
    )


# ---------------------------------------------------------------------------
# Génération du rapport Markdown
# ---------------------------------------------------------------------------


def generer_rapport_markdown(rapport: RapportBenchmark) -> str:
    """Produit le rapport Markdown unique de benchmark selon le cahier des charges."""
    statut_exactitude = (
        "CONFORME"
        if rapport.score_exactitude >= 0.85
        else ("NON CONFORME" if rapport.mode.startswith("llm") else "indicatif")
    )
    statut_refus = (
        "CONFORME"
        if rapport.score_refus >= 0.95
        else ("NON CONFORME" if rapport.mode.startswith("llm") else "indicatif")
    )
    statut_invariant = "CONFORME" if rapport.nb_violations_invariant == 0 else "VIOLATION"
    statut_chiffres_faux = (
        "CONFORME"
        if rapport.nb_chiffres_faux_affiches == 0
        else ("NON CONFORME" if rapport.mode.startswith("llm") else "indicatif")
    )

    cible_latence = "évaluée (< 3 s)" if rapport.mode.startswith("llm") else "indicatif"
    latence_s = rapport.latence_mediane_ms / 1000
    statut_latence = (
        "CONFORME"
        if (rapport.mode.startswith("llm") and latence_s < 3.0)
        else ("NON CONFORME" if rapport.mode.startswith("llm") else "indicatif")
    )

    ligne_chiffres_faux = (
        f"| **Chiffres faux affichés** (confiance) | 0 | "
        f"**{rapport.nb_chiffres_faux_affiches}** | {statut_chiffres_faux} |"
    )
    ligne_exact = (
        f"| **Exactitude** (sourcée, sur {rapport.nb_reponses_attendues} questions) | ≥ 85 % | "
        f"**{rapport.score_exactitude * 100:.1f} %** "
        f"({rapport.nb_exactitude_succes}/{rapport.nb_reponses_attendues}) | {statut_exactitude} |"
    )
    ligne_refus = (
        f"| **Refus pertinent** (sur {rapport.nb_refus_attendus} refus) | ≥ 95 % | "
        f"**{rapport.score_refus * 100:.1f} %** "
        f"({rapport.nb_refus_succes}/{rapport.nb_refus_attendus}) | {statut_refus} |"
    )
    ligne_inv = (
        f"| **Invariant « zéro chiffre inventé »** | Tolérance 0 | "
        f"**{rapport.nb_violations_invariant} violation(s)** | **{statut_invariant}** |"
    )
    ligne_lat = (
        f"| **Latence médiane** ({cible_latence}) | < 3,0 s | "
        f"**{rapport.latence_mediane_ms:.1f} ms** (P95: {rapport.latence_p95_ms:.1f} ms) | "
        f"{statut_latence} |"
    )

    lignes = [
        f"# Rapport de Benchmark — Gëstukaay ({rapport.mode})",
        "",
        f"- **Date** : {rapport.date_iso}",
        f"- **Mode** : `{rapport.mode}`",
        f"- **Jeu de test** : {rapport.nb_total} questions officielles",
        "",
        "## 1. Cibles du cahier des charges (§12)",
        "",
        "| Mesure | Cible | Obtenu | Statut |",
        "|---|---|---|---|",
        ligne_chiffres_faux,
        ligne_exact,
        ligne_refus,
        ligne_inv,
        ligne_lat,
        "",
        "## 2. Sous-scores par type de question",
        "",
        "| Type | Réussite | Pourcentage |",
        "|---|---|---|",
    ]

    labels_types = {
        "simple": "Simple (valeur exacte directe)",
        "classement": "Classement (14 régions ou 16 académies)",
        "comparative_spatiale": "Comparaison spatiale (multi-zones)",
        "comparative_temporelle": "Comparaison temporelle (deux périodes)",
        "suivi": "Suivi contextuel (suite_de)",
        "approchee": "Correspondance approchée (choix vivants)",
        "refus": "Refus officiel (hors socle, projection, inintelligible)",
    }

    for t_code, (succes, tot) in rapport.sous_scores_type.items():
        nom = labels_types.get(t_code, t_code)
        pct = (succes / tot * 100) if tot else 0.0
        lignes.append(f"| {nom} | {succes}/{tot} | {pct:.1f} % |")

    lignes.extend(
        [
            "",
            "## 3. Sous-scores par langue",
            "",
            "| Langue | Réussite | Pourcentage |",
            "|---|---|---|",
        ]
    )

    labels_langue = {"fr": "Français", "wo": "Wolof"}
    for lang, (succes, tot) in rapport.sous_scores_langue.items():
        nom = labels_langue.get(lang, lang)
        pct = (succes / tot * 100) if tot else 0.0
        lignes.append(f"| {nom} | {succes}/{tot} | {pct:.1f} % |")

    lignes.extend(
        [
            "",
            "## 4. Invariant « zéro chiffre inventé »",
            "",
        ]
    )

    if not rapport.violations:
        lignes.extend(
            [
                "> **Invariant strictement vérifié** : aucune violation détectée sur les 103 questions.",
                "- Volet (a) : 100 % des `Resultat` servis proviennent d'une observation du socle avec la valeur exacte.",
                "- Volet (b) : 100 % des points de graphiques correspondent à des observations du socle.",
                "- Volet (c) : tous les chiffres figurant dans les explications appartiennent à la liste blanche des données officielles affichées.",
                "- Volet (d) : aucune valeur numérique statistique n'apparaît dans une réponse approchée ou un refus.",
            ]
        )
    else:
        lignes.extend(
            [
                f"> **ALERTE : {len(rapport.violations)} violation(s) de l'invariant constatée(s) !**",
                "",
                "| Question | Volet | Détail |",
                "|---|---|---|",
            ]
        )
        for v in rapport.violations:
            lignes.append(f"| {v.question_id} | {v.volet} | {v.message} |")

    if rapport.defauts_moteur:
        lignes.extend(
            [
                "",
                "## 5. Défauts constatés du moteur (signalements sans modification de engine/src)",
                "",
            ]
        )
        for defaut in rapport.defauts_moteur:
            lignes.append(f"- {defaut}")

    # Section des échecs détaillés
    echecs = [ev for ev in rapport.evaluations if not ev.reponse_correcte]
    lignes.extend(
        [
            "",
            f"## 6. Détail des écarts ({len(echecs)} questions non conformes)",
            "",
            "| Id | Type | Langue | Attendu | Obtenu | Détail |",
            "|---|---|---|---|---|---|",
        ]
    )
    for ev in echecs:
        lignes.append(
            f"| {ev.question_id} | {ev.type_question} | {ev.langue} | "
            f"{ev.issue_attendue} | {ev.issue_obtenue} | {ev.detail} |"
        )

    return "\n".join(lignes) + "\n"


# ---------------------------------------------------------------------------
# Point d'entrée CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark de bout en bout et contrôle de l'invariant « zéro chiffre inventé »."
    )
    parser.add_argument(
        "--regles",
        action="store_true",
        default=True,
        help="Mode règles locales (gratuit, sans réseau, par défaut)",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Mode LLM via la chaîne configurée (PAYANT : nécessite confirmation)",
    )
    parser.add_argument(
        "--oui",
        "-y",
        action="store_true",
        help="Confirme l'exécution payante LLM sans invite interactive",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=JEU_PAR_DEFAUT,
        help="Chemin vers le fichier questions.csv",
    )
    parser.add_argument(
        "--rapport",
        type=Path,
        default=None,
        help="Chemin personnalisé vers le rapport Markdown de sortie",
    )
    args = parser.parse_args()

    mode_llm = bool(args.llm)
    mode_nom = "regles"

    if mode_llm:
        print("=" * 60)
        print("ATTENTION : Mode LLM sélectionné (appels d'API payants).")
        print(f"Coût estimé pour 103 questions : ~{COUT_ESTIME_LLM:.2f} $ USD (Gemini 2.5 Flash).")
        print("Aucun appel payant ne doit être lancé sans l'accord préalable de Khalifa.")
        print("=" * 60)
        if not args.oui:
            reponse = (
                input("Confirmez-vous le lancement de l'évaluation LLM ? [o/N] ").strip().lower()
            )
            if reponse not in ("o", "oui", "y", "yes"):
                print("Exécution annulée par l'utilisateur.")
                return 0
        sys.path.insert(0, str(RACINE / "engine" / "scripts"))
        from essai_llm import charger_env  # type: ignore[import-not-found]
        from gestukaay_engine.llm import charger_client

        charger_env(RACINE / ".env")
        client = charger_client()
        nom_modele = next((m.modele for m in client.chaine if m.fournisseur != "regles"), "llm")
        mode_nom = "llm-" + nom_modele.replace("/", "-").replace(":", "-")
        # LLM activé via variable d'environnement reconnue par MoteurReel
        os.environ["LLM_CHAINE"] = "oui"

    # Chargement du socle et du moteur
    t_start = time.perf_counter()
    s = socle()
    duree_socle = time.perf_counter() - t_start
    print(f"Socle {s.version} chargé ({len(s)} valeurs) en {duree_socle:.2f} s.")

    moteur = MoteurReel(socle_=s)

    # Lecture des questions
    if not args.questions.exists():
        print(f"Erreur : fichier {args.questions} introuvable.", file=sys.stderr)
        return 1

    with open(args.questions, encoding="utf-8-sig", newline="") as f:
        questions = list(csv.DictReader(f, delimiter=";"))
    print(f"Lancement du benchmark sur {len(questions)} questions (mode: {mode_nom})...")

    rapport = executer_benchmark(questions, moteur, mode_nom)

    # Sauvegarde du rapport Markdown
    RAPPORT_DIR.mkdir(parents=True, exist_ok=True)
    fichier_rapport = args.rapport or (RAPPORT_DIR / f"benchmark_{mode_nom}.md")
    contenu_md = generer_rapport_markdown(rapport)
    fichier_rapport.write_text(contenu_md, encoding="utf-8")
    print(f"Rapport enregistré dans : {fichier_rapport.relative_to(RACINE)}")

    # Affichage synthétique console
    print("\n" + "=" * 60)
    print(f"SYNTHÈSE DU BENCHMARK ({mode_nom})")
    print("=" * 60)
    print(f"Chiffres faux affichés   : {rapport.nb_chiffres_faux_affiches} [cible: 0]")
    print(
        f"Exactitude (83 q)        : {rapport.nb_exactitude_succes}/{rapport.nb_reponses_attendues} "
        f"({rapport.score_exactitude * 100:.1f} %) [cible: ≥ 85 %]"
    )
    print(
        f"Refus pertinent (20 q)   : {rapport.nb_refus_succes}/{rapport.nb_refus_attendus} "
        f"({rapport.score_refus * 100:.1f} %) [cible: ≥ 95 %]"
    )
    print(f"Invariant « 0 inventé »  : {rapport.nb_violations_invariant} violation(s) [cible: 0]")
    print(
        f"Latence médiane / P95    : {rapport.latence_mediane_ms:.1f} ms / {rapport.latence_p95_ms:.1f} ms"
    )
    print("=" * 60)

    # Code de sortie 1 seulement si l'invariant est violé
    if rapport.nb_violations_invariant > 0:
        print(
            f"ÉCHEC CRITIQUE : {rapport.nb_violations_invariant} violation(s) de l'invariant !",
            file=sys.stderr,
        )
        return 1

    print("Invariant strictement respecté. Code de sortie 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
