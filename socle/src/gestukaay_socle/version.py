"""Versions figées du socle extrait (issue #8, décision 0013).

    ../socle_gestukaay/
        2026.10.0/          version publiée : jamais modifiée
            observations.csv  sources.csv  rejets.csv
            VERSION           « 2026.10.0 »
            MANIFEST.json     date, commit Git des référentiels, comptes, empreintes sha256
        brouillon/          extraction de travail, écrasable

Le manifeste prouve que deux machines ont le même socle (mêmes empreintes) et dit avec quels
référentiels il a été produit : si `indicateurs.csv` change sans nouvelle extraction, cela se voit.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .indicateurs import REFERENTIELS

FICHIERS = ("observations.csv", "sources.csv", "rejets.csv")
REFERENTIELS_UTILISES = ("indicateurs.csv", "zones.csv", "domaines.csv", "jeux.csv", "natures.csv",
                         "corrections.csv", "zones_par_jeu.csv", "defauts_desagregation.csv")
FORMAT_VERSION = re.compile(r"^\d{4}\.\d{1,2}\.\d+$")  # 2026.10.0
BROUILLON = "brouillon"


def empreinte(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def commit_git(depot: Path) -> dict:
    """Commit du dépôt au moment de l'extraction, et s'il y avait des modifications non commitées."""
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=depot, capture_output=True, text=True,
                             check=True).stdout.strip()
        sale = subprocess.run(["git", "status", "--porcelain", "--", "socle/referentiels"], cwd=depot,
                              capture_output=True, text=True, check=True).stdout.strip()
        return {"commit": sha, "referentiels_modifies_non_commites": bool(sale)}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "referentiels_modifies_non_commites": None}


def ecrire_manifeste(dossier: Path, version: str, depot: Path, comptes: dict) -> dict:
    """Écrit VERSION et MANIFEST.json une fois les fichiers du socle écrits."""
    manifeste = {
        "version": version,
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        **commit_git(depot),
        "comptes": comptes,
        "fichiers": {f: empreinte(dossier / f) for f in FICHIERS if (dossier / f).exists()},
        "referentiels": {f: empreinte(REFERENTIELS / f) for f in REFERENTIELS_UTILISES
                         if (REFERENTIELS / f).exists()},
    }
    (dossier / "VERSION").write_text(version + "\n", encoding="utf-8")
    (dossier / "MANIFEST.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    return manifeste


def lire_manifeste(dossier: Path) -> dict | None:
    f = dossier / "MANIFEST.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _cle(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in version.split("."))


def dossier_du_socle(chemin: Path) -> Path:
    """Le dossier d'une version : `chemin` lui-même s'il contient le socle, sinon la version publiée
    la plus récente qu'il contient (2026.10.1 > 2026.10.0), sinon le brouillon."""
    if (chemin / "observations.csv").exists():
        return chemin
    versions = sorted((d for d in chemin.iterdir() if d.is_dir() and FORMAT_VERSION.match(d.name)
                       and (d / "observations.csv").exists()), key=lambda d: _cle(d.name)) \
        if chemin.is_dir() else []
    if versions:
        return versions[-1]
    if (chemin / BROUILLON / "observations.csv").exists():
        return chemin / BROUILLON
    raise FileNotFoundError(f"aucun socle extrait dans {chemin} : lancer socle/scripts/extraire.py")


def ecarts_referentiels(dossier: Path) -> list[str]:
    """Référentiels du dépôt différents de ceux qui ont produit cette version du socle."""
    m = lire_manifeste(dossier)
    if not m:
        return []
    return [f for f, h in m.get("referentiels", {}).items()
            if (REFERENTIELS / f).exists() and empreinte(REFERENTIELS / f) != h]
