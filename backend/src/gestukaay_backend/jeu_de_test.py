"""Jeu de test dans le back-office (cahier 5.10, maquette BO-JeuTest) : lancer le benchmark de KBD
(mesure/scripts/benchmark.py, décision 0020) depuis l'API, garder chaque exécution, les comparer.

Le benchmark est exécuté tel quel, sur le moteur réel déjà chargé par l'API :
  - « regles » : compréhension par règles locales, sans réseau ni coût, quelques secondes ;
  - « llm » : la chaîne LLM du .env, environ 0,07 $ et deux à trois minutes pour 103 questions.
Une seule exécution à la fois, en tâche de fond. Avec le faux moteur, rien n'est lancé (503) : le
benchmark n'a de sens que sur le socle réel.
"""

from __future__ import annotations

import csv
import dataclasses
import importlib.util
import json
import os
import sys
import threading
from functools import cache
from pathlib import Path
from types import ModuleType

RACINE = Path(__file__).resolve().parents[3]
SCRIPT = RACINE / "mesure" / "scripts" / "benchmark.py"
QUESTIONS = RACINE / "mesure" / "jeu_de_test" / "questions.csv"
MODES = ("regles", "llm")


def llm_autorise() -> bool:
    """Le mode LLM coûte (environ 0,07 $) et occupe le moteur 2 à 3 minutes dans le même processus que
    les questions des utilisateurs : désactivé par défaut, à ouvrir seulement en local ou hors démo."""
    return os.environ.get("GESTUKAAY_BENCHMARK_LLM", "").lower() in ("oui", "1", "on")

_verrou = threading.Lock()


@cache
def benchmark() -> ModuleType:
    """Le script de KBD, chargé comme un module (mesure/ n'est pas un paquet)."""
    spec = importlib.util.spec_from_file_location("gestukaay_benchmark", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["gestukaay_benchmark"] = module
    spec.loader.exec_module(module)
    return module


@cache
def questions() -> list[dict[str, str]]:
    with QUESTIONS.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def resume_questions() -> list[dict[str, str]]:
    """Ce que l'écran affiche d'une question : jamais les valeurs attendues (inutile ici)."""
    return [{k: q[k] for k in ("id", "question", "type", "langue", "issue_attendue")} for q in questions()]


def moteur_pour(moteur, mode: str):
    """Le moteur réel de l'API (mode llm) ou une copie qui comprend par règles (mode regles),
    sur le même socle déjà chargé. None si l'API tourne sur le faux moteur."""
    if not hasattr(moteur, "socle"):
        return None
    if mode == "llm":
        return moteur
    from gestukaay_engine.comprehension import Comprehension
    from gestukaay_engine.moteur import MoteurReel

    return MoteurReel(socle_=moteur.socle, comprehension=Comprehension(None))


def en_dict(rapport) -> dict:
    """RapportBenchmark -> JSON : tout, sauf rien d'interne (les violations restent, c'est l'invariant)."""
    return json.loads(json.dumps(dataclasses.asdict(rapport), ensure_ascii=False, default=str))


def resume(resultat: dict) -> dict:
    """Les chiffres de tête d'une exécution, pour la liste et les tuiles."""
    cles = ("mode", "date_iso", "nb_total", "nb_reponses_attendues", "nb_exactitude_succes", "score_exactitude",
            "nb_refus_attendus", "nb_refus_succes", "score_refus", "nb_chiffres_faux_affiches",
            "nb_violations_invariant", "latence_mediane_ms", "latence_p95_ms")
    return {k: resultat.get(k) for k in cles}


def lancer(executer, stockage, mode: str, moteur) -> str:
    """Crée l'exécution, puis lance le benchmark en tâche de fond (`executer` : un thread en service,
    un appel direct dans les tests). RuntimeError si une exécution est déjà en cours."""
    if not _verrou.acquire(blocking=False):
        raise RuntimeError("une exécution est déjà en cours")
    eid = stockage.creer_execution(mode)

    def tache():
        try:
            rapport = benchmark().executer_benchmark(questions(), moteur, mode)
            stockage.terminer_execution(eid, en_dict(rapport))
        except Exception as e:  # noqa: BLE001 — l'échec est gardé avec l'exécution, rien ne remonte
            stockage.terminer_execution(eid, None, f"{type(e).__name__} : {e}")
        finally:
            _verrou.release()

    try:
        executer(tache)
    except Exception:
        _verrou.release()
        raise
    return eid
