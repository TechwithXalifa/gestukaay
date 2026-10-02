"""Évalue la compréhension (#10) sur les 103 questions du jeu de test.

    uv run python engine/scripts/evaluer_comprehension.py --regles   # sans réseau, gratuit
    uv run python engine/scripts/evaluer_comprehension.py            # chaîne LLM du .env : COÛTE (≈ 103 appels)

Compare, question par question : l'intention, l'indicateur (celui que le jeu de test attend,
d'après le référentiel), les zones et la période. Les questions de suivi sont posées après
leur question précédente, avec son contexte. Écrit mesure/rapports/comprehension_<mode>.md.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

from gestukaay_engine.comprehension import Comprehension
from gestukaay_socle.indicateurs import indicateurs

RACINE = Path(__file__).resolve().parents[2]
JEU = RACINE / "mesure" / "jeu_de_test" / "questions.csv"
INTENTION = {"simple": "valeur", "comparative": "comparaison", "classement": "classement",
             "approchee": "valeur", "suivi": "valeur", "refus": "hors_perimetre"}
ZONE_FIXE = {"feujxob"}  # prix relevés à Dakar : aucune zone à citer


def attendu(q: dict, codes: dict[str, set]) -> dict:
    intention = INTENTION[q["type"]]
    if q["type"] == "suivi" and len(q["zones_attendues"].split("|")) > 1:
        intention = "comparaison"  # « Et en 2025 ? » après « Chômage à Dakar et à Thiès »
    if q["motif"] == "projection":
        intention = "valeur"  # la question est comprise ; c'est la résolution qui refuse
    zones = None
    if q["issue_attendue"] == "exacte" and q["type"] in ("simple", "comparative"):
        zones = set() if q["zones_attendues"] == "SN" or q["dataset_id"] in ZONE_FIXE \
            else set(q["zones_attendues"].split("|"))
    # période : celle du jeu de test ; « derniere » si la question n'en cite pas ; sinon non notée
    # (questions approchées et refus : l'année citée est lue, la résolution décide)
    periode = None if q["periode_par_defaut"] == "oui" else q["periode"].split("|")[0] if q["periode"] else "*"
    return {"intention": intention, "indicateurs": codes.get(q["id"], set()), "zones": zones,
            "periode": periode}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--regles", action="store_true", help="règles locales seulement, sans réseau")
    args = p.parse_args()
    if args.regles:
        comp, mode = Comprehension(None), "regles"
    else:
        sys.path.insert(0, str(RACINE / "engine" / "scripts"))
        from essai_llm import charger_env  # même lecture du .env que l'essai du client (#9)
        from gestukaay_engine.llm import charger_client
        charger_env(RACINE / ".env")
        client = charger_client()
        modele = next((m.modele for m in client.chaine if m.fournisseur != "regles"), "llm")
        comp, mode = Comprehension(client), "llm-" + modele.replace("/", "-").replace(":", "-")

    with open(JEU, encoding="utf-8-sig", newline="") as f:
        questions = list(csv.DictReader(f, delimiter=";"))
    codes: dict[str, set] = {}
    for x in indicateurs().values():
        for q in x.questions_test:
            codes.setdefault(q, set()).add(x.code)

    resultats, requetes, lignes = [], {}, []
    for q in sorted(questions, key=lambda q: bool(q["suite_de"])):  # les précédentes d'abord
        texte = q["question"]
        contexte = [requetes[q["suite_de"]]] if q["suite_de"] in requetes else None
        c = comp.comprendre(texte, contexte)
        requetes[q["id"]] = c.requete
        a, r = attendu(q, codes), c.requete
        ok = {
            "intention": r.intention == a["intention"],
            "indicateur": (not a["indicateurs"]) or r.indicateur in a["indicateurs"],
            # « au Sénégal » (SN) et aucune zone citée disent la même chose : national
            "zones": a["zones"] is None or set(r.zones) == a["zones"] or (not a["zones"] and r.zones == ["SN"]),
            "periode": True if a["periode"] == "*" else (r.periode.type == "derniere") if a["periode"] is None
            else r.periode.valeur == a["periode"],
        }
        latence = c.appel.latence_ms if c.appel else 0
        resultats.append((q, ok, latence, c))
        if not all(ok.values()):
            faux = ", ".join(k for k, v in ok.items() if not v)
            lignes.append(f"| {q['id']} | {texte} | {faux} | {r.intention} · {r.indicateur} · "
                          f"{','.join(r.zones) or '—'} · {r.periode.valeur or 'dernière'} | "
                          f"{a['intention']} · {' / '.join(sorted(a['indicateurs'])) or '—'} |")

    def taux(filtre, cle=None):
        sel = [ok for q, ok, _, _ in resultats if filtre(q)]
        bons = sum(all(ok.values()) if cle is None else ok[cle] for ok in sel)
        return f"{bons}/{len(sel)} ({100 * bons / max(len(sel), 1):.0f} %)"

    def tous(q):
        return True

    L = [f"# Compréhension — évaluation ({mode})", "",
         (f"{len(resultats)} questions du jeu de test (#10). Une question est juste si l'intention, "
          "l'indicateur, les zones et la période le sont."), "",
         "| | Score |", "|---|---|",
         f"| **Tout juste** | **{taux(tous)}** |",
         f"| Français | {taux(lambda q: q['langue'] == 'fr')} |",
         f"| Wolof | {taux(lambda q: q['langue'] == 'wo')} |",
         f"| Intention | {taux(tous, 'intention')} |",
         f"| Indicateur | {taux(tous, 'indicateur')} |",
         f"| Zones | {taux(tous, 'zones')} |",
         f"| Période | {taux(tous, 'periode')} |"]
    latences = [lat for _, _, lat, c in resultats if c.source == "llm"]
    if latences:
        couts = [c.appel.cout_usd for _, _, _, c in resultats if c.appel and c.appel.cout_usd]
        L += [f"| Latence médiane / max | {statistics.median(latences):.0f} ms / {max(latences)} ms |",
              f"| Secours par règles | {sum(c.source == 'regles' for *_, c in resultats)} |",
              f"| Coût total | {sum(couts):.4f} $ |" if couts else "| Coût | inconnu |"]
    L += ["", "## Questions fausses", "", "| Id | Question | Faux | Obtenu | Attendu |", "|---|---|---|---|---|",
          *lignes]
    sortie = RACINE / "mesure" / "rapports" / f"comprehension_{mode}.md"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[4:13]))
    print(f"Rapport : {sortie.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
