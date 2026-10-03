"""Versions figées du socle (#8, décision 0013). Dossiers temporaires : tourne en CI."""

import json

import pytest
from gestukaay_socle.version import (
    REFERENTIELS_UTILISES,
    dossier_du_socle,
    ecarts_referentiels,
    ecrire_manifeste,
    empreinte,
)


def socle_factice(dossier, contenu="a;b\n"):
    dossier.mkdir(parents=True)
    for f in ("observations.csv", "sources.csv", "rejets.csv"):
        (dossier / f).write_text(contenu, encoding="utf-8")
    return dossier


def test_manifeste(tmp_path):
    d = socle_factice(tmp_path / "2026.10.0")
    m = ecrire_manifeste(d, "2026.10.0", tmp_path, {"valeurs": 1})
    assert (d / "VERSION").read_text().strip() == "2026.10.0"
    assert json.loads((d / "MANIFEST.json").read_text())["fichiers"] == m["fichiers"]
    assert m["fichiers"]["observations.csv"] == empreinte(d / "observations.csv")
    assert set(m["referentiels"]) <= set(REFERENTIELS_UTILISES) and "indicateurs.csv" in m["referentiels"]
    assert ecarts_referentiels(d) == []  # produit avec les référentiels actuels


def test_version_la_plus_recente_sinon_brouillon(tmp_path):
    socle_factice(tmp_path / "brouillon")
    assert dossier_du_socle(tmp_path).name == "brouillon"
    for v in ("2026.10.0", "2026.10.2", "2026.9.9"):
        socle_factice(tmp_path / v)
    assert dossier_du_socle(tmp_path).name == "2026.10.2"  # numérique, pas alphabétique
    assert dossier_du_socle(tmp_path / "2026.10.0").name == "2026.10.0"  # dossier de version direct
    with pytest.raises(FileNotFoundError):
        dossier_du_socle(tmp_path / "vide")


def test_referentiel_modifie_depuis_l_extraction(tmp_path):
    d = socle_factice(tmp_path / "2026.10.0")
    m = ecrire_manifeste(d, "2026.10.0", tmp_path, {})
    m["referentiels"]["indicateurs.csv"] = "0" * 64
    (d / "MANIFEST.json").write_text(json.dumps(m), encoding="utf-8")
    assert ecarts_referentiels(d) == ["indicateurs.csv"]
