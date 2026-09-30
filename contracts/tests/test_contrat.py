"""Garde-fous du contrat. Tournent en CI à chaque PR."""

import json
import re
from pathlib import Path

import pytest
from gestukaay_contracts.models import AskResponse, ReponseApprochee
from pydantic import ValidationError

EXEMPLES = sorted((Path(__file__).parents[1] / "examples").glob("*.json"))
GENERATED = Path(__file__).parents[1] / "generated"


@pytest.mark.parametrize("chemin", EXEMPLES, ids=lambda p: p.stem)
def test_exemple_conforme(chemin):
    AskResponse.model_validate_json(chemin.read_text(encoding="utf-8"))


@pytest.mark.parametrize("chemin", EXEMPLES, ids=lambda p: p.stem)
def test_toute_valeur_a_sa_source(chemin):
    """Engagement 01 : aucune valeur sans source."""
    rep = AskResponse.model_validate_json(chemin.read_text(encoding="utf-8")).reponse
    for r in getattr(rep, "resultats", []):
        assert r.source.libelle and r.source.date_publication and r.source.url


def test_approchee_ne_peut_pas_porter_de_valeur():
    """EF-06 / US-03 : impossible, par construction, d'ajouter une valeur."""
    data = json.loads((Path(__file__).parents[1] / "examples/approchee.json").read_text())
    data["reponse"]["resultats"] = [{"valeur": 1}]
    with pytest.raises(ValidationError):
        AskResponse.model_validate(data)
    assert "resultats" not in ReponseApprochee.model_fields


@pytest.mark.parametrize("chemin", EXEMPLES, ids=lambda p: p.stem)
def test_format_des_nombres(chemin):
    """7.4 : séparateur de milliers = espace fine insécable (U+202F)."""
    rep = AskResponse.model_validate_json(chemin.read_text(encoding="utf-8")).reponse
    for r in getattr(rep, "resultats", []):
        assert re.fullmatch(r"-?\d{1,3}( \d{3})*(,\d+)?", r.valeur_affichee), r.valeur_affichee


def test_schemas_generes_a_jour():
    """Le schéma committé doit correspondre aux modèles (sinon : scripts/generer_contrat.sh)."""
    from gestukaay_contracts.export import MODELES, schema_de

    for nom, (modele, mode) in MODELES.items():
        fichier = GENERATED / f"{nom}.schema.json"
        assert fichier.exists(), f"{fichier} manquant : lancer scripts/generer_contrat.sh"
        assert json.loads(fichier.read_text()) == schema_de(modele, mode), (
            f"{fichier.name} n'est pas à jour : lancer scripts/generer_contrat.sh"
        )
