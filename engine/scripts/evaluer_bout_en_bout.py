"""Bout en bout : compréhension (#10) puis résolution (#11) sur le jeu de test.

    uv run python engine/scripts/evaluer_bout_en_bout.py --regles   # sans réseau, gratuit
    uv run python engine/scripts/evaluer_bout_en_bout.py            # chaîne LLM du .env : COÛTE (≈ 103 appels)

Chaque valeur rendue est comparée, au chiffre près, à la valeur attendue du jeu de test.
L'indicateur qui compte d'abord : **chiffres faux affichés = 0** (engagement « zéro chiffre
inventé »). Une question sans réponse n'est pas un chiffre faux ; une valeur pour la mauvaise
zone, période ou indicateur en est un.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter
from pathlib import Path

from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.resolution import Introuvable, resoudre
from gestukaay_engine.socle import socle

RACINE = Path(__file__).resolve().parents[2]
JEU = RACINE / "mesure" / "jeu_de_test" / "questions.csv"


def attendus(q: dict) -> set[tuple[str, str, float]]:
    periodes = q["periode"].split("|")
    out = set()
    for item in q["valeurs_attendues"].split("|"):
        cle, valeur = item.rsplit("=", 1)
        z, p = cle.split("@") if "@" in cle else (cle, periodes[0])
        out.add((z, p, float(valeur)))
    return out


def classer(q: dict, r) -> tuple[str, str]:
    """(catégorie, détail). Catégories : juste, faux, sans_reponse, refus_ok, servi_a_tort, hors_11."""
    obtenu = set() if isinstance(r, Introuvable) else {(x.zone.code, x.periode.valeur, x.valeur)
                                                       for x in r.resultats}
    detail = r.raison + " : " + r.detail if isinstance(r, Introuvable) else \
        " ; ".join(f"{z} {p} = {v:g}" for z, p, v in sorted(obtenu))
    if q["type"] == "classement" or "|" in q["periode"]:
        return "hors_11", detail  # classement (#14) ; deux périodes : limite du contrat
    if q["issue_attendue"] == "exacte":
        if not obtenu:
            return "sans_reponse", detail
        return ("juste" if obtenu == attendus(q) else "faux"), detail
    # approchée ou refus : aucune valeur exacte ne doit sortir de #11
    return ("refus_ok" if not obtenu else "servi_a_tort"), detail


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--regles", action="store_true", help="règles locales seulement, sans réseau")
    args = p.parse_args()
    if args.regles:
        comp, mode = Comprehension(None), "regles"
    else:
        sys.path.insert(0, str(RACINE / "engine" / "scripts"))
        from essai_llm import charger_env
        from gestukaay_engine.llm import charger_client
        charger_env(RACINE / ".env")
        client = charger_client()
        modele = next((m.modele for m in client.chaine if m.fournisseur != "regles"), "llm")
        comp, mode = Comprehension(client), "llm-" + modele.replace("/", "-").replace(":", "-")
    t = time.perf_counter()
    s = socle()
    chargement = time.perf_counter() - t

    with open(JEU, encoding="utf-8-sig", newline="") as f:
        questions = list(csv.DictReader(f, delimiter=";"))
    requetes, lignes, compte, durees = {}, [], Counter(), []
    for q in sorted(questions, key=lambda q: bool(q["suite_de"])):
        contexte = [requetes[q["suite_de"]]] if q["suite_de"] in requetes else None
        c = comp.comprendre(q["question"], contexte)
        requetes[q["id"]] = c.requete
        t = time.perf_counter()
        r = resoudre(s, c.requete, q["langue"], q["question"], c.lieux_inconnus)
        durees.append((time.perf_counter() - t) * 1000)
        cat, detail = classer(q, r)
        compte[cat] += 1
        if cat not in ("juste", "refus_ok"):
            attendu = "|".join(f"{z} {p} = {v:g}" for z, p, v in sorted(attendus(q))) \
                if q["issue_attendue"] == "exacte" else q["issue_attendue"]
            lignes.append(f"| {q['id']} | {q['question']} | **{cat}** | {c.requete.indicateur} | {detail} | {attendu} |")

    exactes = sum(compte[k] for k in ("juste", "faux", "sans_reponse"))
    autres = compte["refus_ok"] + compte["servi_a_tort"]
    L = [f"# Bout en bout — compréhension + résolution ({mode})", "",
         (f"Socle : {len(s)} valeurs chargées en {chargement:.1f} s ; résolution : "
          f"{sorted(durees)[len(durees) // 2]:.1f} ms en médiane."), "",
         "| | |", "|---|---|",
         f"| **Chiffres faux affichés** | **{compte['faux'] + compte['servi_a_tort']}** |",
         f"| Questions exactes : valeur juste au chiffre près | {compte['juste']}/{exactes} |",
         f"| Questions exactes : sans réponse | {compte['sans_reponse']}/{exactes} |",
         f"| Approchées et refus : aucune valeur servie | {compte['refus_ok']}/{autres} |",
         f"| Hors #11 (classement #14, deux périodes : contrat) | {compte['hors_11']} |", "",
         "## À traiter", "", "| Id | Question | Résultat | Indicateur compris | Obtenu | Attendu |",
         "|---|---|---|---|---|---|", *lignes]
    sortie = RACINE / "mesure" / "rapports" / f"bout_en_bout_{mode}.md"
    sortie.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[2:12]))
    print(f"Rapport : {sortie.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
