"""Structure du jeu de test (#18). Tourne en CI, sans le socle brut."""

import csv
import json
from collections import Counter
from pathlib import Path

import pytest
from gestukaay_socle.zones import zones

JEU = Path(__file__).parents[1] / "jeu_de_test" / "questions.csv"
with open(JEU, encoding="utf-8-sig", newline="") as _f:
    QUESTIONS = list(csv.DictReader(_f, delimiter=";"))
PAR_ID = {q["id"]: q for q in QUESTIONS}

# Répartition validée (cahier 12.1 : 70 FR / 30 WO), portée à 103 en #3 pour garder 20 refus
REPARTITION = {
    ("fr", "simple"): 29, ("fr", "comparative"): 11, ("fr", "classement"): 7,
    ("fr", "approchee"): 8, ("fr", "refus"): 14, ("fr", "suivi"): 3,
    ("wo", "simple"): 13, ("wo", "comparative"): 4, ("wo", "classement"): 3,
    ("wo", "approchee"): 3, ("wo", "refus"): 6, ("wo", "suivi"): 2,
}
ISSUE_PAR_TYPE = {"simple": "exacte", "comparative": "exacte", "classement": "exacte",
                  "suivi": "exacte", "approchee": "approchee", "refus": "aucune"}


def test_questions_reparties_comme_convenu():
    assert len(QUESTIONS) == 103
    assert len(PAR_ID) == 103, "identifiants en double"
    assert Counter((q["langue"], q["type"]) for q in QUESTIONS) == REPARTITION


@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q["id"])
def test_question_coherente(q):
    assert q["issue_attendue"] == ISSUE_PAR_TYPE[q["type"]]
    # FR : la question est écrite ; WO : au moins son sens en français
    assert q["question"] if q["langue"] == "fr" else q["equivalent_fr"]
    for z in filter(None, q["zones_attendues"].split("|")):
        assert z in zones(), f"zone inconnue : {z}"
    if q["issue_attendue"] == "exacte":
        assert q["dataset_id"] and q["valeurs_attendues"] and q["periode"]
        json.loads(q["filtres"])
    elif q["issue_attendue"] == "approchee":
        # EF-06 : aucune valeur avant confirmation
        assert q["zones_attendues"] and not q["valeurs_attendues"]
    else:
        assert q["motif"] in ("hors_socle", "projection", "incomprehension")
        assert not q["valeurs_attendues"]
    # WO : écrite par un locuteur, et son type d'écriture indiqué (score séparé)
    if q["langue"] == "wo":
        assert q["question"] and q["ecriture"] in ("officielle", "usage")
    else:
        assert not q["ecriture"]
    if q["type"] == "suivi":
        precedente = PAR_ID[q["suite_de"]]
        assert precedente["langue"] == q["langue"]


def test_variantes_wolof_alignees_sur_les_questions_francaises():
    with open(JEU.parent / "variantes_wolof.csv", encoding="utf-8-sig", newline="") as f:
        variantes = list(csv.DictReader(f, delimiter=";"))
    francaises = [q for q in QUESTIONS if q["langue"] == "fr"]
    assert [v["id"] for v in variantes] == [q["id"] for q in francaises]
    for v, q in zip(variantes, francaises, strict=True):
        assert v["question_fr"] == q["question"] and v["question_wo"]
        assert v["ecriture"] in ("officielle", "usage")
