"""Vérification d'un socle figé reçu (release, CI #20) : empreintes du manifeste."""

import json
import sys
from pathlib import Path

from gestukaay_socle.version import empreinte

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verifier_socle import verifier


def socle_fige(dossier: Path) -> Path:
    dossier.mkdir()
    (dossier / "observations.csv").write_text("observation_id;valeur\nx;1\n", encoding="utf-8")
    (dossier / "sources.csv").write_text("source_id\nx\n", encoding="utf-8")
    manifeste = {"version": "2026.10.0",
                 "fichiers": {f: empreinte(dossier / f) for f in ("observations.csv", "sources.csv")}}
    (dossier / "MANIFEST.json").write_text(json.dumps(manifeste), encoding="utf-8")
    return dossier


def test_socle_intact(tmp_path):
    assert verifier(socle_fige(tmp_path / "2026.10.0"), "2026.10.0") == []


def test_fichier_modifie_ou_absent(tmp_path):
    d = socle_fige(tmp_path / "2026.10.0")
    (d / "observations.csv").write_text("observation_id;valeur\nx;2\n", encoding="utf-8")
    (d / "sources.csv").unlink()
    assert verifier(d) == ["observations.csv : empreinte différente du manifeste", "sources.csv absent"]


def test_mauvaise_version_ou_sans_manifeste(tmp_path):
    d = socle_fige(tmp_path / "2026.10.0")
    assert verifier(d, "2026.10.1") == ["version '2026.10.0' au lieu de '2026.10.1'"]
    (d / "MANIFEST.json").unlink()
    assert verifier(d) == [f"{d}/MANIFEST.json absent"]
