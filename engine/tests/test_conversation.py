"""Messages qui ne sont pas des questions de statistique (décision 0033, contrat 1.5.0)."""

import pytest
from gestukaay_contracts.models import AskRequest
from gestukaay_engine.conversation import CATEGORIES, _textes, regles, texte
from gestukaay_engine.langue import detecter
from test_moteur import MOTEUR


@pytest.mark.parametrize("message, categorie", [
    ("comment tu vas", "salutation"), ("Comment tu vas ?", "salutation"), ("ça va ?", "salutation"),
    ("Salam naka leu", "salutation"), ("Naka nga def", "salutation"), ("Assalamou aleykoum", "salutation"),
    ("Lou bess", "salutation"), ("Ya ngi ci djam", "salutation"), ("Bonjour", "salutation"),
    ("merci", "remerciement"), ("Merci beaucoup !", "remerciement"), ("Au revoir", "au_revoir"),
    ("qui es-tu ?", "a_propos"), ("d'où viennent tes chiffres ?", "a_propos"), ("Tu parles wolof ?", "langue"),
    ("Que sais-tu faire ?", "aide"), ("c'est quoi le taux de pauvreté ?", "definition"),
    ("Pourquoi le chômage augmente ?", "pourquoi"), ("Que pensez-vous du chômage ?", "pourquoi"),
])
def test_categories_par_regles(message, categorie):
    assert regles(message) == categorie


@pytest.mark.parametrize("message", [
    "Combien d'habitants à Thiès ?", "Ñaata nit ñoo dëkk Tiés ?", "Salam, ñaata nit ñoo dëkk Tiés ?",
    "Bonjour, combien d'habitants à Thiès ?", "naka la limu askan wi tollu ci kaolack", "Quel est le PIB ?",
    "Naka météo bi di mel euleuk ?",  # hors sujet : seul le LLM le classe ; en règles, refus comme avant
])
def test_une_question_n_est_pas_une_conversation(message):
    assert regles(message) is None


def test_chaque_categorie_a_son_texte():
    assert set(CATEGORIES) <= set(_textes())
    assert all(fr.strip() for fr, _ in _textes().values())


def test_wolof_vide_part_en_francais():  # choix de KBD (0032) tant que le wolof n'est pas écrit
    fr, wo = _textes()["salutation"]
    assert texte("salutation", "wo") == (wo or fr)


@pytest.mark.parametrize("message", ["comment tu vas", "ça va ?", "merci", "qui es-tu ?"])
def test_petits_mots_francais_detectes(message):  # « comment tu vas » partait en wolof
    assert detecter(message) == "fr"


def test_salutation_n_est_pas_un_refus():
    r = MOTEUR.repondre(AskRequest(question="comment tu vas")).reponse
    assert (r.issue, r.motif) == ("aucune", "conversation") and r.suggestions == []
    assert "n'existe pas" not in r.message and r.langue == "fr"


def test_pourquoi_propose_le_chiffre_verifie():
    r = MOTEUR.repondre(AskRequest(question="Pourquoi le chômage augmente à Dakar ?")).reponse
    assert r.motif == "conversation" and r.message == texte("pourquoi")
    assert [s.indicateur.code for s in r.suggestions] == ["dwibrlf"]


def test_definition_absente_propose_le_chiffre():
    r = MOTEUR.repondre(AskRequest(question="c'est quoi la population ?")).reponse
    assert r.motif == "conversation" and r.suggestions


def test_pourquoi_sans_chiffre_verifiable_reste_poli():
    # le socle de test n'a pas le chômage national : pas de suggestion inventée, message de hors sujet
    r = MOTEUR.repondre(AskRequest(question="Pourquoi le chômage augmente ?")).reponse
    assert r.motif == "conversation" and r.suggestions == [] and r.message == texte("hors_sujet")
