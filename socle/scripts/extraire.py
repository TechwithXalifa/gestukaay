"""Extraction du socle brut vers le schéma du cahier (issues #4, #5, #6, #8).

    uv run python socle/scripts/extraire.py                       # brouillon, écrasable
    uv run python socle/scripts/extraire.py --version 2026.10.0   # version publiée, figée

Lit $GESTUKAAY_SOCLE_BRUT/{observations,catalogue}.csv et les référentiels ; écrit dans
../socle_gestukaay/<version>/ (ou --sortie), hors Git :
  - observations.csv : une ligne par valeur (schéma 10.3), avec sa nature et sa ligne d'origine ;
  - sources.csv : une ligne par jeu du portail ;
  - rejets.csv : chaque valeur écartée et son motif (dont les corrections de #6) ;
  - VERSION et MANIFEST.json : version, commit Git des référentiels, empreintes (décision 0013).
Une version publiée n'est jamais réécrite : nouvelle version = nouveau dossier.
Rapports versionnés : socle/rapports/extraction.md et controles.md.

Contrôle de bout en bout : chaque valeur attendue du jeu de test doit se retrouver, une seule
fois et à l'identique, dans la table extraite. Échoue (code 1) sinon.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from gestukaay_socle.controles import (
    appliquer,
    controle_population,
    controler,
    corrections,
    unites_incrementees,
)
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
from gestukaay_socle.version import BROUILLON, FORMAT_VERSION, ecrire_manifeste
from gestukaay_socle.zones import zones

RACINE = Path(__file__).resolve().parents[2]
SOCLE = Path(os.environ.get("GESTUKAAY_SOCLE_BRUT", RACINE.parent / "socle_opendata_par_themes"))
RACINE_SOCLES = RACINE.parent / "socle_gestukaay"
SORTIE = RACINE_SOCLES / BROUILLON  # fixé par main() selon --version / --sortie
JEU = RACINE / "mesure" / "jeu_de_test" / "questions.csv"
RAPPORT = RACINE / "socle" / "rapports" / "extraction.md"
RAPPORT_CONTROLES = RACINE / "socle" / "rapports" / "controles.md"


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


def rapport_controles(observations, corr, exclusions) -> None:
    """Corrections appliquées, puis ce que les contrôles signalent encore (#6, décision 0008)."""
    ind = indicateurs()
    L = ["# Contrôles du socle", "",
         ("Les **corrections** (`socle/referentiels/corrections.csv`) sont décidées à la main, avec leur preuve. "
          "Les **contrôles** signalent seulement : rien n'est exclu sans une ligne de corrections."), "",
         "## Corrections appliquées", "", "| Id | Action | Jeu | Effet | Motif | Preuve |", "|---|---|---|---|---|---|"]
    for c in corr:
        if c.action == "exclure":
            effet = f"{exclusions.get(c.id, 0)} valeurs exclues"
        else:
            n = sum(1 for x in ind.values() if x.dataset_id == c.dataset_id and x.unite_affichee == c.valeur)
            effet = f"unité affichée « {c.valeur} » ({n} indicateurs)"
        L.append(f"| {c.id} | {c.action} | `{c.dataset_id}` | {effet} | {c.motif} | {c.preuve} |")
    L += ["", "## Contrôle entre sources : population régionale", "",
          "`rnumqzf` 2022 comparé au RGPH-5 2023 (`pvswjnd`) : un écart de plus de 15 % trahit une permutation.", ""]
    L += [f"- {e}" for e in controle_population(observations)] or ["Aucun écart."]
    unites = unites_incrementees(ind)
    L += ["", "## Unités incrémentées (portail)", "",
          ", ".join(f"`{d}` ({n} années de base)" for d, n in sorted(unites.items())) or "Aucune.",
          "(corrigées pour l'affichage par C05 à C07 ; l'unité du portail reste l'identité de l'indicateur)", ""]
    L += ["## Signalements restants", "", "| Contrôle | Signalements | Exemples |", "|---|---|---|"]
    signal = controler(observations, ind)
    for nom in ("pourcentage hors de 0-100", "Gini hors de ]0, 1[", "date impossible",
                "rupture (×3 d'une année sur l'autre)"):
        ex = signal.get(nom, [])
        L.append(f"| {nom} | {len(ex)} | {'<br>'.join(ex[:5])[:900]} |")
    ruptures = Counter(e.split("`")[1].split(".")[0].split("~")[0] for e in signal.get(
        "rupture (×3 d'une année sur l'autre)", []))
    if ruptures:
        L += ["", "Ruptures par jeu (à examiner ; une vraie rupture reste servie) : "
              + ", ".join(f"`{d}` ({n})" for d, n in ruptures.most_common(20)) + "."]
    RAPPORT_CONTROLES.write_text("\n".join(L) + "\n", encoding="utf-8")


def _p1() -> set[str]:
    return {x.code for x in indicateurs().values() if x.priorite == "P1"}


def main() -> int:
    global SORTIE
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--version", help="version publiée, ex. 2026.10.0 (sinon : brouillon écrasable)")
    p.add_argument("--sortie", type=Path, help="dossier de sortie (défaut : ../socle_gestukaay/<version>)")
    args = p.parse_args()
    if args.version and not FORMAT_VERSION.match(args.version):
        sys.exit(f"version « {args.version} » : attendu AAAA.MM.N, ex. 2026.10.0")
    version = args.version or BROUILLON
    SORTIE = args.sortie or RACINE_SOCLES / version
    if args.version and (SORTIE / "VERSION").exists():
        sys.exit(f"{SORTIE} existe déjà : une version publiée ne se réécrit pas (nouvelle version = "
                 "nouveau dossier).")
    if not (SOCLE / "observations.csv").exists():
        sys.exit(f"{SOCLE}/observations.csv introuvable : définir GESTUKAAY_SOCLE_BRUT.")
    SORTIE.mkdir(parents=True, exist_ok=True)
    geo = colonnes_geo(lignes_brutes())
    with open(SOCLE / "catalogue.csv", encoding="utf-8-sig", newline="") as f:
        annees_maj = {r["dataset_id"]: r["derniere_maj"][:4] for r in csv.DictReader(f)}
    res = extraire(lignes_brutes(numeros=True), geo, index_indicateurs(indicateurs()), zones_par_jeu(),
                   natures(), annees_maj)
    corr = corrections()
    res.observations, rejets_corr, exclusions = appliquer(res.observations, corr)
    res.rejets = sorted(res.rejets + rejets_corr, key=lambda r: r[0])
    ecrire("observations.csv", COLONNES_OBSERVATIONS, res.observations)
    ecrire("rejets.csv", COLONNES_REJETS, res.rejets)
    ecrire("sources.csv", COLONNES_SOURCES, sources())
    total, erreurs, non_observees = verifier_jeu_de_test(res.observations)
    rapport(res, total, erreurs, non_observees)
    rapport_controles(res.observations, corr, exclusions)
    if erreurs:  # une version ne se fige jamais avec une valeur attendue manquante
        (SORTIE / "VERSION").unlink(missing_ok=True)
    else:
        m = ecrire_manifeste(SORTIE, version, RACINE, {
            "valeurs": len(res.observations), "rejets": len(res.rejets),
            "indicateurs": len({o[1] for o in res.observations}), "jeu_de_test": f"{total}/{total}"})
        print(f"Version {version} : {len(m['fichiers'])} fichiers, commit {str(m['commit'])[:7]}"
              + (" (référentiels modifiés non commités !)" if m["referentiels_modifies_non_commites"] else ""))
    print(f"{res.stats['valeurs lues']} valeurs lues : {len(res.observations)} extraites, "
          f"{len(res.rejets)} rejetées -> {SORTIE}")
    print(f"Jeu de test : {total - len(erreurs)}/{total} valeurs attendues retrouvées")
    for e in erreurs:
        print("  ÉCHEC", e)
    print(f"Corrections : {sum(exclusions.values())} valeurs exclues ({dict(exclusions)})")
    print(f"Rapports : {RAPPORT.relative_to(RACINE)}, {RAPPORT_CONTROLES.relative_to(RACINE)}")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
