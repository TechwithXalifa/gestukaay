"""Garde-fous du contrat. Tournent en CI à chaque PR."""

import json
import re
from pathlib import Path

import pytest
from gestukaay_contracts.models import (
    AskResponse,
    ReponseApprochee,
    SituateRequest,
    SituateResponse,
    TranscriptionResponse,
)
from pydantic import ValidationError

DOSSIER = Path(__file__).parents[1] / "examples"
# Exemples qui ne sont pas des AskResponse (routes v1.1.0)
AUTRES = {"transcription.json": TranscriptionResponse, "situer.json": SituateResponse}
EXEMPLES = sorted(p for p in DOSSIER.glob("*.json") if p.name not in AUTRES)
GENERATED = Path(__file__).parents[1] / "generated"


@pytest.mark.parametrize("nom,modele", AUTRES.items())
def test_exemples_des_autres_routes_conformes(nom, modele):
    modele.model_validate_json((DOSSIER / nom).read_text(encoding="utf-8"))


def test_situer_toute_valeur_a_sa_source_et_aucune_tranche():
    rep = SituateResponse.model_validate_json((DOSSIER / "situer.json").read_text(encoding="utf-8"))
    for r in [rep.moyenne_region, rep.moyenne_pays, *rep.contexte]:
        assert r.source.libelle and r.source.date_publication and r.source.url
    # décision 0004 §2 : aucune notion de décile ou de quintile du ménage lui-même
    assert "decile" not in SituateResponse.model_fields and "quintile" not in SituateResponse.model_fields


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
    data = json.loads((Path(__file__).parents[1] / "examples/approchee.json").read_text(encoding="utf-8"))
    data["reponse"]["resultats"] = [{"valeur": 1}]
    with pytest.raises(ValidationError):
        AskResponse.model_validate(data)
    assert "resultats" not in ReponseApprochee.model_fields


def test_une_projection_est_toujours_etiquetee():
    """Décision 0002 : une projection affichée porte sa nature et sa base."""
    for chemin in EXEMPLES:
        rep = AskResponse.model_validate_json(chemin.read_text(encoding="utf-8")).reponse
        for r in getattr(rep, "resultats", []):
            if r.nature == "projection":
                assert r.base_projection


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
        assert json.loads(fichier.read_text(encoding="utf-8")) == schema_de(modele, mode), (
            f"{fichier.name} n'est pas à jour : lancer scripts/generer_contrat.sh"
        )


def test_tranches_v130_additives():
    """v1.3.0 (décision 0012) : les trois nouvelles tranches passent, l'ancienne aussi."""
    for tranche in ("500k_750k", "750k_1m", "plus_1m", "plus_500k"):
        assert SituateRequest(region="SN-DK", taille_menage=7, depenses_mensuelles=tranche)


def test_motif_non_disponible_v130():
    rep = json.loads((DOSSIER / "aucune_incomprehension.json").read_text(encoding="utf-8"))
    rep["reponse"]["motif"] = "non_disponible"
    rep["reponse"]["message"] = "Ce type de question n'est pas encore disponible."
    assert AskResponse.model_validate(rep).reponse.motif == "non_disponible"
