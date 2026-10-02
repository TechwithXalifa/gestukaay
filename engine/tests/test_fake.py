import pytest
from gestukaay_contracts.models import AskRequest
from gestukaay_engine import charger_moteur


@pytest.mark.parametrize(
    "question,issue",
    [
        ("Combien d'habitants à Thiès ?", "exacte"),
        ("Population de Dakar et de Thiès en 2023", "exacte"),
        ("Population de la ville de Thiès en 2023", "approchee"),
        ("Combien de personnes parlent sérère au Sénégal ?", "aucune"),
        ("Population du Sénégal en 2040", "aucune"),
        ("Espérance de vie en 2035", "exacte"),
        ("bla bla bla", "aucune"),
    ],
)
def test_moteur_factice_couvre_les_trois_issues(question, issue):
    rep = charger_moteur().repondre(AskRequest(question=question))
    assert rep.reponse.issue == issue


def test_moteur_factice_transcrire_et_situer():
    from gestukaay_contracts.models import SituateRequest

    m = charger_moteur()
    assert m.transcrire(b"...", "webm").transcription
    rep = m.situer(SituateRequest(region="SN-KD", taille_menage=7, depenses_mensuelles="100k_200k"))
    assert rep.position_region in ("en_dessous", "autour", "au_dessus")


def test_moteur_factice_refus_hors_socle():
    rep = charger_moteur().repondre(AskRequest(question="Combien de personnes parlent sérère au Sénégal ?"))
    assert rep.reponse.motif == "hors_socle" and len(rep.reponse.suggestions) == 3
