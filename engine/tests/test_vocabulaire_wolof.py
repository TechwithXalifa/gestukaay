"""Vocabulaire wolof validé par KBD (#22, #23, décision 0009) : lieux, mots, marqueurs."""

import pytest
from gestukaay_contracts.models import AskRequest
from gestukaay_engine.candidats import ORDRE_ASC, SYNONYMES, lieux_inconnus, zones_citees
from gestukaay_engine.comprehension import _COMPARAISON, _TEMPS, Comprehension
from gestukaay_socle.zones import normaliser
from test_moteur import MOTEUR


@pytest.mark.parametrize("question, zone", [
    ("ñaata jigéen ñoo dëkk seajo", "SN-SE"), ("ñaata nit ñoo dëkk seju", "SN-SE"),
    ("ñaata nit ñoo dëkk Njaaréem", "SN-DB"), ("limu askanu kawlak", "SN-KL"), ("kaolag", "SN-KL"),
    ("ñaata nit ñoo dëkk maatam", "SN-MT"), ("taux scolaire dakaar", "SN-DK"), ("Njaambuur", "SN-LG"),
    ("Kédugu", "SN-KE"), ("Kedugu", "SN-KE"), ("Tambakunda", "SN-TC"), ("kees", "SN-TH"),
])
def test_noms_wolof_des_lieux(question, zone):
    assert zones_citees(question) == [zone]


@pytest.mark.parametrize("question, lieu", [
    ("Ñaata nit ñoo dëkk Tuubaa ?", "Tuubaa"), ("Population de Richard-Toll", "Richard Toll"),
    ("ñaata nit ñoo dëkk risaar tol", "Risaar Tol"), ("population ville de kolda", "ville de kolda"),
])
def test_lieu_rattache_reconnu_sans_preposition(question, lieu):
    assert lieu in lieux_inconnus(question)


def test_touba_en_wolof_ne_devient_jamais_le_senegal():
    r = MOTEUR.repondre(AskRequest(question="Ñaata nit ñoo dëkk Tuubaa ?")).reponse
    assert r.issue != "exacte"


def test_mots_et_marqueurs():
    assert set(SYNONYMES["nakk"]) == {"pauvrete", "vaccines"}  # ñakk (vaccin) et ñàkk (manquer)
    assert ORDRE_ASC.search(normaliser("ban diwaan moo gëna néew"))
    assert ORDRE_ASC.search(normaliser("ban diiwaan moo gëna tuuti"))
    assert _COMPARAISON.search(normaliser("ndax prix ceeb bi yokku na")) and _COMPARAISON.search(normaliser("wàññiku"))
    assert _TEMPS.search(normaliser("chomage ren")) and _TEMPS.search(normaliser("population daaw"))


def test_classement_wolof_le_moins_pauvre():
    r = Comprehension(None).comprendre("ban diwaan moo gëna néew tolluwaayu ñàkk").requete
    assert (r.intention, r.ordre) == ("classement", "asc")
