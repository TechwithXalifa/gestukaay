"""Fiches des jeux et des indicateurs P1 (issue #7).

    uv run python socle/scripts/fiches.py

Lit les descriptions du portail dans $GESTUKAAY_SOCLE_BRUT/brut/*/*.json et écrit :
  - socle/referentiels/jeux.csv : une fiche par jeu (définition, opération, méthode…) ;
  - socle/rapports/fiches_p1.md : la fiche complète des indicateurs P1, à relire.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

from gestukaay_socle.fiches import COLONNES_JEUX, FICHIER_JEUX, decouper, jeux
from gestukaay_socle.indicateurs import indicateurs

RACINE = Path(__file__).resolve().parents[2]
SOCLE = Path(os.environ.get("GESTUKAAY_SOCLE_BRUT", RACINE.parent / "socle_opendata_par_themes"))
RAPPORT = RACINE / "socle" / "rapports" / "fiches_p1.md"


def descriptions() -> dict[str, str]:
    out = {}
    for f in sorted((SOCLE / "brut").glob("*/*.json")):
        m = json.loads(f.read_text(encoding="utf-8"))["metadonnees"]
        out[m["id"]] = m.get("rawDescription") or m.get("description") or ""
    return out


def ecrire_jeux(desc: dict[str, str]) -> list[dict]:
    lignes = []
    for ds, texte in sorted(desc.items()):
        r = {k: "" for k in COLONNES_JEUX} | decouper(texte) | {"dataset_id": ds}
        lignes.append(r)
    with FICHIER_JEUX.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES_JEUX, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(lignes)
    jeux.cache_clear()
    return lignes


def definition(x, j) -> str:
    """Définition propre, sinon celle du jeu s'il ne décrit que cet indicateur."""
    if x.definition:
        return x.definition
    if j and not x.dimension_indicateur and (j.definition or j.description):
        return j.definition or f"(description du jeu) {j.description[:400]}{'…' if len(j.description) > 400 else ''}"
    return "**aucune définition sur le portail**"


def rapport() -> None:
    L = ["# Fiches des indicateurs P1", "",
         ("Relecture (#7) : chaque fiche réunit le référentiel des indicateurs et la fiche du jeu, découpée "
         "dans la description du portail. La définition propre à l'indicateur (colonne `definition` de "
         "`indicateurs.csv`) est **citée du portail**, jamais rédigée ; à défaut, celle du jeu s'applique."), ""]
    for x in sorted((x for x in indicateurs().values() if x.priorite == "P1"), key=lambda x: x.code):
        j = jeux().get(x.dataset_id)
        niveaux = ", ".join(x.niveaux_zone) or "national (sans colonne géographique)"
        L += [f"## {x.libelle_fr}", "",
              f"*{x.libelle_wo or '—'}* · `{x.code}` · {x.verification}", "",
              "| | |", "|---|---|",
              f"| Unité | {x.unite_affichee or x.unite or '—'} |",
              f"| Définition | {definition(x, j)} |",
              f"| Méthode | {(j.methode if j else '') or '—'} |",
              f"| Opération | {(j.operation if j else '') or '—'} |",
              f"| Producteur | {x.producteur} |",
              f"| Zones | {niveaux} |",
              f"| Période | {x.periode_debut} → {x.periode_fin} |",
              f"| Jeu | {x.jeu} |",
              f"| Questions du jeu de test | {', '.join(x.questions_test)} |"]
        if x.note:
            L.append(f"| Réserve | {x.note} |")
        L.append("")
    RAPPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    if not (SOCLE / "brut").exists():
        sys.exit(f"{SOCLE}/brut introuvable : définir GESTUKAAY_SOCLE_BRUT.")
    lignes = ecrire_jeux(descriptions())
    structurees = sum(bool(r["definition"]) for r in lignes)
    vides = sum(not r["definition"] and not r["description"] for r in lignes)
    print(f"{len(lignes)} jeux : {structurees} au modèle des annuaires, {len(lignes) - structurees - vides} "
          f"en texte libre, {vides} sans description -> {FICHIER_JEUX.relative_to(RACINE)}")
    rapport()
    print(f"Rapport : {RAPPORT.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
