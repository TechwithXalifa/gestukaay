"""Messages qui ne sont pas des questions de statistique (décision 0033, contrat 1.5.0)."""

import pytest
from gestukaay_contracts.models import AskRequest
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.conversation import (
    CATEGORIES,
    _textes,
    naka_sujet,
    regles,
    sans_politesse,
    texte,
)
from gestukaay_engine.langue import detecter
from gestukaay_engine.moteur import MoteurReel
from test_moteur import MOTEUR


@pytest.mark.parametrize("message, categorie", [
    ("comment tu vas", "salutation"), ("Comment tu vas ?", "salutation"), ("ça va ?", "salutation"),
    ("Salam naka leu", "salutation"), ("Naka nga def", "salutation"), ("Assalamou aleykoum", "salutation"),
    ("Lou bess", "salutation"), ("Ya ngi ci djam", "salutation"), ("Bonjour", "salutation"),
    ("merci", "remerciement"), ("Merci beaucoup !", "remerciement"), ("Au revoir", "au_revoir"),
    ("Ba beneen yoon", "au_revoir"), ("Jërëjëf", "remerciement"),
    ("qui es-tu ?", "a_propos"), ("d'où viennent tes chiffres ?", "a_propos"), ("Tu parles wolof ?", "langue"),
    ("Que sais-tu faire ?", "aide"), ("c'est quoi le taux de pauvreté ?", "definition"),
    ("Pourquoi le chômage augmente ?", "pourquoi"), ("Que pensez-vous du chômage ?", "pourquoi"),
])
def test_categories_par_regles(message, categorie):
    assert regles(message) == categorie


@pytest.mark.parametrize("message", [
    "Combien d'habitants à Thiès ?", "Ñaata nit ñoo dëkk Tiés ?", "Salam, ñaata nit ñoo dëkk Tiés ?",
    "Bonjour, combien d'habitants à Thiès ?", "naka la limu askan wi tollu ci kaolack", "Quel est le PIB ?",
])
def test_une_question_n_est_pas_une_conversation(message):
    assert regles(message) is None


def test_chaque_categorie_a_son_texte():
    assert set(CATEGORIES) <= set(_textes())
    assert all(fr.strip() for fr, _ in _textes().values())


def test_textes_wolof_de_kbd():  # écrits par KBD le 07/10 (0009), sigle écrit à l'écrit (0032)
    assert all(wo.strip() for _, wo in _textes().values())
    assert texte("salutation", "wo").startswith("Maa ngi fi rekk, jërëjëf !")
    assert "ANSD" in texte("a_propos", "wo") and "A-EN-ES-DE" not in texte("a_propos", "wo")
    assert texte("definition", "wo", definition="X.") == "X. Ndax bëgg nga xam lim bi ?"


def test_salutation_en_wolof_repond_en_wolof():
    r = MOTEUR.repondre(AskRequest(question="Salam naka leu")).reponse
    assert r.langue == "wo" and r.message == texte("salutation", "wo")


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




# --- Revue de SAN sur #140 --------------------------------------------------------------------------------


@pytest.mark.parametrize("message, reste", [
    ("Bonjour, combien d'habitants à Thiès ?", "combien d'habitants à Thiès ?"),
    ("Salut ! Quel est le taux de pauvreté à Kolda ?", "Quel est le taux de pauvreté à Kolda ?"),
    ("Merci. Et à Dakar ?", "Et à Dakar ?"), ("Salam, ñaata nit ñoo dëkk Tiés ?", "ñaata nit ñoo dëkk Tiés ?"),
    ("Naka nga def, ñaata nit ñoo dëkk Kaolack ?", "ñaata nit ñoo dëkk Kaolack ?"),
    ("Bonjour", "Bonjour"), ("Merci beaucoup !", "Merci beaucoup !"), ("Merci beaucoup", "Merci beaucoup"),
    ("Naka njëg ceeb", "Naka njëg ceeb"),  # « naka » + mot n'est pas une politesse fixe
])
def test_politesse_de_tete_retiree(message, reste):
    assert sans_politesse(message) == reste


def test_bonjour_puis_question_repond_au_chiffre_meme_si_le_llm_dit_salutation():
    # le LLM gardait parfois la politesse seule : la politesse est retirée AVANT lui, il ne voit que la question
    vus = []

    class Llm(Comprehension):
        def comprendre(self, question, contexte=None):
            vus.append(question)
            return super().comprendre(question, contexte)

    m = MoteurReel(MOTEUR.socle, Llm(None))
    r = m.repondre(AskRequest(question="Bonjour, combien d'habitants à Thiès ?")).reponse
    assert vus == ["combien d'habitants à Thiès ?"] and r.issue == "exacte"
    assert r.question == "Bonjour, combien d'habitants à Thiès ?"  # la réponse garde la question posée


@pytest.mark.parametrize("message", ["Naka njëg ceeb", "Naka mbëj bi", "Naka Kaolack ?"])
def test_naka_suivi_d_un_sujet_n_est_pas_une_salutation(message):
    assert regles(message) is None and naka_sujet(message)


def test_pourquoi_sans_chiffre_ne_promet_rien():
    r = MOTEUR.repondre(AskRequest(question="Pourquoi le chômage augmente ?")).reponse
    assert r.suggestions == [] and r.message == texte("pourquoi_sans_chiffre")
    assert not r.message.rstrip().endswith(":")


def test_forme_sure_prime_sur_un_llm_qui_ne_comprend_pas():
    # essai réel du 07/10 : le LLM jugeait « naka leu » incompréhensible ; la salutation de KBD prime
    from gestukaay_engine.comprehension import SortieLLM

    class LlmPerdu:
        def structurer(self, systeme, message, modele):
            return SortieLLM(intention="hors_perimetre", confiance=0.2, incomprehensible=True), None

    c = Comprehension(LlmPerdu()).comprendre("Salam naka leu")
    assert c.conversation == "salutation" and not c.incomprehensible
    assert sans_politesse("Salam naka leu") == "Salam naka leu"  # tout le message est la salutation


@pytest.mark.parametrize("message", [
    "Qui est le président du Sénégal ?", "Quel temps fera-t-il demain à Dakar ?", "Écris-moi un poème sur la Casamance",
    "Kan mooy njiitu réewum Senegaal ?", "Naka météo bi di mel euleuk ?", "Raconte-moi une blague",
])
def test_hors_sujet_evident_par_regles(message):  # jeu de test : FR-059, FR-060, FR-063, WO-025, WO-026
    assert regles(message) == "hors_sujet"

