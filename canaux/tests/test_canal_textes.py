"""Textes fixes (wolof de KBD, tel quel) et mots de commande (décision 0025)."""

import pytest
from gestukaay_canaux.textes import bouton_liste, commande, est_salutation, texte


def test_accueil_bilingue_tel_qu_ecrit_par_kbd():
    assert texte("accueil") == (
        "Dalal ak jàmm ci Gëstukaay ! Bienvenue ! Posez votre question sur les statistiques officielles "
        "du Sénégal (wolof / français).\nBindal sa laaj / Exemple : « Ñaata nit ñoo dëkk Tiés ? »")


def test_texte_fixe_wolof_puis_francais():
    lignes = texte("vocal_pas_encore").split("\n")
    assert lignes == ["Mënuma déglu audios yi ba leegi : bindal sa laaj ci mbind.",
                      "Je ne peux pas écouter les notes vocales pour le moment : écrivez votre question."]


def test_bouton_de_liste_20_caracteres_au_plus():
    assert bouton_liste() == "Tànnal / Choisir" and len(bouton_liste()) <= 20


@pytest.mark.parametrize("message, attendu", [
    ("ndimbal", "aide"), ("Dimbëli", "aide"), ("?", "aide"), ("help", "aide"),
    ("misaal", "exemples"), ("Làkk", "langue"), ("TAXAW", "stop"), ("bayyi", "stop"), ("arrêt", "stop"),
    ("1", "1"), ("Benn", "1"), ("1.", "1"), ("Ñaar !", "2"), ("nyaar", "2"), ("ñett", "3"), ("trois", "3"),
])
def test_commandes_fr_et_wo(message, attendu):
    assert commande(message) == attendu


@pytest.mark.parametrize("message", ["Combien d'habitants à Thiès ?", "bayyi naa", "un taux", "2023", ""])
def test_une_phrase_n_est_pas_une_commande(message):
    assert commande(message) is None


@pytest.mark.parametrize("message", [  # formes de KBD (07/10), avec écritures francisées
    "/start", "Salam Naka leu", "Naka nga def ?", "nanga def", "Na ngeen def", "nakamou", "Lou bess",
    "naka affaire yi", "Ya ngi ci djam", "naka souba si", "Naka beuceug bi", "Jàmm nga am", "djam nga am",
    "Assalamou aleykoum", "Salam aleykoum, naka nga def", "Bonjour", "salut !", "naka mbir mi",
    "naka leu",  # KBD : « naka » + un mot = salutation
])
def test_salutations_de_kbd(message):
    assert est_salutation(message)


@pytest.mark.parametrize("message", [
    "Salam, ñaata nit ñoo dëkk Tiés ?", "Bonjour, combien d'habitants à Thiès ?",
    "Naka la limu askan wi tollu ci Kaolack ?",  # « naka » qui ouvre une vraie question (plus de 3 mots)
    "Combien d'habitants à Thiès ?", "Ñaata kër ñoo am kuraŋ ci Senegaal ?", "salamandre",
    "Naka njëg ceeb", "Naka mbëj bi", "Naka Kaolack ?",  # « naka » + un sujet ou un lieu (revue de SAN)
])
def test_une_question_n_est_pas_une_salutation(message):
    assert not est_salutation(message)
