"""Vérifie chaque réponse attendue du jeu de test dans le socle brut (issue #18).

    uv run python mesure/scripts/verifier_attendus.py

Pour chaque question à issue « exacte », retrouve dans
$GESTUKAAY_SOCLE_BRUT/observations.csv la ligne désignée par
(dataset_id, filtres, zone, période) et vérifie :
  - qu'il en existe exactement UNE (sinon la question est ambiguë) ;
  - que sa valeur est identique à la valeur attendue.
Échoue (code 1) à la moindre différence. Aucune valeur n'est donc écrite
à la main dans le jeu de test sans être prouvée par le socle.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from gestukaay_socle.zones import niveau_de_colonne, resoudre

RACINE = Path(__file__).resolve().parents[2]
SOCLE = Path(os.environ.get("GESTUKAAY_SOCLE_BRUT", RACINE.parent / "socle_opendata_par_themes"))
JEU = RACINE / "mesure" / "jeu_de_test" / "questions.csv"


def periode(p: str, freq: str) -> str:
    """Période du portail -> format du jeu : 2023, 2026-03, 2023-T2."""
    if freq == "M":
        return p[:7]
    if freq == "Q":
        return f"{p[:4]}-T{(int(p[5:7]) - 1) // 3 + 1}"
    return p[:4]


def zone(row: dict, colonne: str, dataset: str) -> str:
    if not colonne:
        # Prix relevés dans l'agglomération de Dakar ; le reste est national.
        return "SN-DK" if dataset == "feujxob" else "SN"
    return resoudre(row.get(colonne, ""), niveau_de_colonne(colonne)) or "?"


def attendus(question: dict) -> list[tuple[str, str, float]]:
    """valeurs_attendues -> [(zone, période, valeur)]."""
    periodes = question["periode"].split("|")
    out = []
    for item in question["valeurs_attendues"].split("|"):
        cle, valeur = item.rsplit("=", 1)
        z, p = cle.split("@") if "@" in cle else (cle, periodes[0])
        out.append((z, p, float(valeur)))
    return out


def main() -> int:
    with open(JEU, encoding="utf-8-sig", newline="") as f:
        questions = [q for q in csv.DictReader(f, delimiter=";") if q["issue_attendue"] == "exacte"]
    jeux = {q["dataset_id"] for q in questions}

    csv.field_size_limit(2**31 - 1)  # sys.maxsize déborde sous Windows (long C sur 32 bits)
    lignes: dict[str, list] = defaultdict(list)
    with open(SOCLE / "observations.csv", encoding="utf-8-sig", newline="") as f:
        for l in csv.DictReader(f):
            if l["valeur"] and l["dataset_id"] in jeux:
                dims = json.loads(l["desagregation_json"] or "{}")
                lignes[l["dataset_id"]].append((periode(l["periode"], l["frequence"]), float(l["valeur"]), dims))

    erreurs = 0
    for q in questions:
        filtres = json.loads(q["filtres"])
        for z, p, v in attendus(q):
            trouvees = [val for per, val, dims in lignes[q["dataset_id"]]
                        if per == p and all(dims.get(k) == x for k, x in filtres.items())
                        and zone(dims, q["colonne_zone"], q["dataset_id"]) == z]
            if len(trouvees) != 1 or trouvees[0] != v:
                erreurs += 1
                print(f"ÉCHEC {q['id']} {z}@{p} : attendu {v}, trouvé {trouvees}")
    total = sum(len(attendus(q)) for q in questions)
    print(f"{len(questions)} questions exactes, {total} valeurs vérifiées, {erreurs} échec(s).")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
