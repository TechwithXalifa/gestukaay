"""Vérifie qu'un dossier de socle figé est intact : empreintes du manifeste et version (décision 0013).

    uv run python socle/scripts/verifier_socle.py ../socle_gestukaay/2026.10.0 [--version 2026.10.0]

Utilisé par la CI (#20) après le téléchargement de la release, et par quiconque reçoit le socle :
chaque fichier de MANIFEST.json doit exister et avoir l'empreinte sha256 notée. Code de sortie 1
sinon : on ne mesure jamais le moteur sur un socle altéré.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from gestukaay_socle.version import empreinte, lire_manifeste


def verifier(dossier: Path, version: str | None = None) -> list[str]:
    """Liste des écarts (vide si le socle est intact)."""
    manifeste = lire_manifeste(dossier)
    if manifeste is None:
        return [f"{dossier}/MANIFEST.json absent"]
    ecarts = []
    if version and manifeste.get("version") != version:
        ecarts.append(f"version {manifeste.get('version')!r} au lieu de {version!r}")
    fichiers = manifeste.get("fichiers") or {}
    if not fichiers:
        ecarts.append("aucune empreinte dans MANIFEST.json")
    for nom, attendue in fichiers.items():
        f = dossier / nom
        if not f.exists():
            ecarts.append(f"{nom} absent")
        elif empreinte(f) != attendue:
            ecarts.append(f"{nom} : empreinte différente du manifeste")
    return ecarts + liens_des_sources(dossier)


PORTAIL = "https://senegal.opendataforafrica.org/"


def liens_des_sources(dossier: Path) -> list[str]:
    """#165 : chaque réponse garde un lien vers la page du jeu sur le portail. Chaque source citée par une
    observation existe dans sources.csv, avec l'adresse https://senegal.opendataforafrica.org/<source_id>."""
    s_csv, o_csv = dossier / "sources.csv", dossier / "observations.csv"
    if not s_csv.exists() or not o_csv.exists():
        return []
    with o_csv.open(encoding="utf-8", newline="") as f:
        lecteur = csv.DictReader(f, delimiter=";")
        if "source_id" not in (lecteur.fieldnames or []):
            return []
        citees = {r["source_id"] for r in lecteur if r["source_id"]}
    with s_csv.open(encoding="utf-8", newline="") as f:
        urls = {r["source_id"]: (r.get("url") or "").strip() for r in csv.DictReader(f, delimiter=";")}
    ecarts = [f"source {s} citée par les observations, absente de sources.csv" for s in sorted(citees - urls.keys())]
    ecarts += [f"source {s} : lien du portail manquant ou inattendu ({u or 'vide'})" for s, u in sorted(urls.items())
               if s in citees and u != PORTAIL + s]
    return ecarts


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("dossier", type=Path)
    p.add_argument("--version", help="version attendue (ex. 2026.10.0)")
    args = p.parse_args()
    ecarts = verifier(args.dossier, args.version)
    for e in ecarts:
        print(f"ÉCART : {e}", file=sys.stderr)
    if ecarts:
        return 1
    print(f"Socle {args.dossier.name} intact : empreintes conformes au manifeste.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
