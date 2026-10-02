"""Extraction du socle brut vers le schéma du cahier (issue #4).

    uv run python socle/scripts/extraire.py

Lit $GESTUKAAY_SOCLE_BRUT/{observations,catalogue}.csv et le référentiel des
indicateurs ; écrit dans $GESTUKAAY_SOCLE_EXTRAIT (défaut : ../socle_gestukaay,
hors Git) :
  - observations.csv : une ligne par valeur (schéma 10.3), avec sa ligne d'origine ;
  - sources.csv : une ligne par jeu du portail ;
  - rejets.csv : chaque valeur écartée et son motif ;
et le rapport socle/rapports/extraction.md (versionné).

Contrôle de bout en bout : chaque valeur attendue du jeu de test doit se
retrouver, une seule fois et à l'identique, dans la table extraite. Échoue
(code 1) sinon.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from gestukaay_socle.extraction import (
    COLONNES_OBSERVATIONS,
    COLONNES_REJETS,
    COLONNES_SOURCES,
    colonnes_geo,
    extraire,
    index_indicateurs,
    natures,
    zones_par_jeu,
)
from gestukaay_socle.indicateurs import dimensions_indicateur, indicateurs
from gestukaay_socle.zones import zones

RACINE = Path(__file__).resolve().parents[2]
SOCLE = Path(os.environ.get("GESTUKAAY_SOCLE_BRUT", RACINE.parent / "socle_opendata_par_themes"))
SORTIE = Path(os.environ.get("GESTUKAAY_SOCLE_EXTRAIT", RACINE.parent / "socle_gestukaay"))
JEU = RACINE / "mesure" / "jeu_de_test" / "questions.csv"
RAPPORT = RACINE / "socle" / "rapports" / "extraction.md"


def lignes_brutes(numeros: bool = False):
    """Lignes de observations.csv, avec leur numéro de ligne dans le fichier si demandé."""
    csv.field_size_limit(2**31 - 1)  # sys.maxsize déborde sous Windows (long C sur 32 bits)
    with open(SOCLE / "observations.csv", encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f)
        for ligne in lecteur:
            yield (lecteur.line_num, ligne) if numeros else ligne


def ecrire(nom: str, colonnes, lignes) -> None:
    with open(SORTIE / nom, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(colonnes)
        w.writerows(lignes)


def sources() -> list[tuple]:
    with open(SOCLE / "catalogue.csv", encoding="utf-8-sig", newline="") as f:
        return [(r["dataset_id"], r["producteur"], r["source"], r["nom"], r["date_publication"][:10],
                 r["derniere_maj"][:10], r["licence"], r["fiche_portail"], r["reference"])
                for r in csv.DictReader(f)]


def attendus(q: dict) -> list[tuple[str, str, float]]:
    """valeurs_attendues -> [(zone, période, valeur)] (même format que mesure/scripts/verifier_attendus.py)."""
    periodes = q["periode"].split("|")
    out = []
    for item in q["valeurs_attendues"].split("|"):
        cle, valeur = item.rsplit("=", 1)
        z, p = cle.split("@") if "@" in cle else (cle, periodes[0])
        out.append((z, p, float(valeur)))
    return out


def verifier_jeu_de_test(observations) -> tuple[int, list[str]]:
    """Chaque valeur attendue doit être trouvée une seule fois, à l'identique."""
    with open(JEU, encoding="utf-8-sig", newline="") as f:
        questions = [q for q in csv.DictReader(f, delimiter=";") if q["issue_attendue"] == "exacte"]
    par_question = defaultdict(set)
    for x in indicateurs().values():
        for q in x.questions_test:
            par_question[q].add(x.code)
    utiles = set().union(*par_question.values())
    par_code = defaultdict(list)
    for o in observations:
        if o[1] in utiles:
            par_code[o[1]].append(o)
    total, erreurs, non_observees = 0, [], []
    for q in questions:
        filtres = json.loads(q["filtres"])
        for k in dimensions_indicateur(filtres):
            filtres.pop(k)  # porté par le code de l'indicateur
        for z, p, v in attendus(q):
            total += 1
            lignes = [o for c in par_question[q["id"]] for o in par_code[c]
                      if o[2] == z and o[4] == p
                      and all(json.loads(o[5]).get(k) == x for k, x in filtres.items())]
            if [float(o[6]) for o in lignes] != [v]:
                erreurs.append(f"{q['id']} {z}@{p} : attendu {v}, trouvé {[o[6] for o in lignes]}")
            elif lignes[0][10] != "observee":
                non_observees.append(f"{q['id']} {z}@{p} : {lignes[0][10]} ({lignes[0][11] or 'base non déclarée'})")
    return total, erreurs, non_observees


def rapport(res, total_attendus: int, erreurs: list[str], non_observees: list[str]) -> None:
    s, obs, rej = res.stats, res.observations, res.rejets
    z = zones()
    niveaux = Counter(z[o[2]].niveau for o in obs)
    presumees = [o for o in obs if o[3]]
    L = ["# Extraction du socle", "",
         (f"Socle brut : `{SOCLE.name}/observations.csv` · sortie : `{SORTIE.name}/` (hors Git) · "
          "schéma du cahier 10.3 (décision #4)."), "",
         "## Résumé", "", "| | Valeurs |", "|---|---|",
         f"| Valeurs non vides lues | {s['valeurs lues']} |",
         f"| → extraites | {len(obs)} |",
         f"| → doublons identiques fusionnés | {s['doublons identiques fusionnés']} |",
         f"| → rejetées (voir `rejets.csv`) | {len(rej)} |",
         f"| Indicateurs représentés | {len({o[1] for o in obs})} |",
         (f"| Zones : pays / régions / départements / académies | {niveaux['pays']} / {niveaux['region']}"
          f" / {niveaux['departement']} / {niveaux['academie']} |"),
         (f"| Zone présumée (jeu sans colonne géographique → Sénégal) | {len(presumees)} valeurs, "
          f"{len({o[9] for o in presumees})} jeux |"), "",
         "## Contrôle de bout en bout : jeu de test", "",
         (f"{total_attendus} valeurs attendues (questions exactes) cherchées dans la table extraite : "
         f"**{total_attendus - len(erreurs)} trouvées à l'identique**, {len(erreurs)} échec(s)."), ""]
    L += [f"- {e}" for e in erreurs] + ([""] if erreurs else [])
    if non_observees:
        L += ["Réponses attendues qui ne sont pas des valeurs observées (le badge doit s'afficher) :", ""]
        L += [f"- {n}" for n in non_observees] + [""]
    L += ["## Nature des valeurs (#5, décision 0007)", "", "| Nature | Valeurs | Jeux |", "|---|---|---|"]
    for nat in ("observee", "estimation", "projection"):
        os_ = [o for o in obs if o[10] == nat]
        L.append(f"| {nat} | {len(os_)} | {len({o[9] for o in os_})} |")
    auto = Counter(o[9] for o in obs if o[10] == "projection" and not o[11])
    L += ["", "Projections repérées par la règle automatique (année postérieure à la dernière mise à jour du "
          "jeu), sans base déclarée dans `natures.csv` : "
          + (", ".join(f"`{d}` ({n})" for d, n in auto.most_common()) or "aucune") + ".", ""]
    L += ["## Rejets par motif", "", "| Motif | Valeurs | Jeux | Exemples |", "|---|---|---|---|"]
    par_motif = defaultdict(list)
    for r in rej:
        par_motif[r[3]].append(r)
    for m, rs in sorted(par_motif.items(), key=lambda x: -len(x[1])):
        ex = ", ".join(sorted({r[4] for r in rs})[:3])
        L.append(f"| {m} | {len(rs)} | {len({r[1] for r in rs})} | {ex[:120]} |")
    conflits = Counter(r[1] for r in rej if r[3] == "doublon conflictuel")
    if conflits:
        L += ["", "### Doublons conflictuels (à trancher en #6)", "",
              ("Même indicateur, zone, période et désagrégation, mais valeurs différentes (souvent une "
              "région et un département de même nom rangés dans la même colonne)."), "",
              "| Jeu | Valeurs |", "|---|---|"] + [f"| `{d}` | {n} |" for d, n in conflits.most_common(15)]
    L += ["", "## Jeux à zone présumée", "",
          ("Sans colonne géographique ni code région : rattachés au Sénégal. À confirmer à la vérification "
          "des indicateurs ; une exception se déclare dans `socle/referentiels/zones_par_jeu.csv`."), "",
          f"{len({o[9] for o in presumees})} jeux ; parmi eux, utilisés par le jeu de test : "
          + (", ".join(f"`{d}`" for d in sorted({o[9] for o in presumees if o[1] in _p1()})) or "aucun") + "."]
    RAPPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def _p1() -> set[str]:
    return {x.code for x in indicateurs().values() if x.priorite == "P1"}


def main() -> int:
    if not (SOCLE / "observations.csv").exists():
        sys.exit(f"{SOCLE}/observations.csv introuvable : définir GESTUKAAY_SOCLE_BRUT.")
    SORTIE.mkdir(parents=True, exist_ok=True)
    geo = colonnes_geo(lignes_brutes())
    with open(SOCLE / "catalogue.csv", encoding="utf-8-sig", newline="") as f:
        annees_maj = {r["dataset_id"]: r["derniere_maj"][:4] for r in csv.DictReader(f)}
    res = extraire(lignes_brutes(numeros=True), geo, index_indicateurs(indicateurs()), zones_par_jeu(),
                   natures(), annees_maj)
    ecrire("observations.csv", COLONNES_OBSERVATIONS, res.observations)
    ecrire("rejets.csv", COLONNES_REJETS, res.rejets)
    ecrire("sources.csv", COLONNES_SOURCES, sources())
    total, erreurs, non_observees = verifier_jeu_de_test(res.observations)
    rapport(res, total, erreurs, non_observees)
    print(f"{res.stats['valeurs lues']} valeurs lues : {len(res.observations)} extraites, "
          f"{len(res.rejets)} rejetées -> {SORTIE}")
    print(f"Jeu de test : {total - len(erreurs)}/{total} valeurs attendues retrouvées")
    for e in erreurs:
        print("  ÉCHEC", e)
    print(f"Rapport : {RAPPORT.relative_to(RACINE)}")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
