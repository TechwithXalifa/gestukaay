import pytest
from gestukaay_contracts.models import AskRequest
from gestukaay_engine import charger_moteur


@pytest.mark.parametrize(
    "question,issue",
    [
        ("Combien d'habitants à Thiès ?", "exacte"),
        ("Population de Dakar et de Thiès en 2023", "exacte"),
        ("Population de la ville de Thiès en 2023", "approchee"),
        ("Nombre de voitures à Kolda", "aucune"),
        ("Population du Sénégal en 2040", "aucune"),
        ("bla bla bla", "aucune"),
    ],
)
def test_moteur_factice_couvre_les_trois_issues(question, issue):
    rep = charger_moteur().repondre(AskRequest(question=question))
    assert rep.reponse.issue == issue
