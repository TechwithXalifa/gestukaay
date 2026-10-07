"""Vocabulaire wolof validé par KBD (#22, #23, décision 0009) : lieux, mots, marqueurs."""

import pytest
from gestukaay_contracts.models import AskRequest
from gestukaay_engine.candidats import (
    ORDRE_ASC,
    SYNONYMES,
    desagregation_citee,
    index,
    lieux_inconnus,
    texte_normalise,
    zones_citees,
)
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


# --- Électricité en wolof (questions de KBD, 06/10) : ŋ, kër, gox-goxaan, gëna ñàkk ---------------------


def _comprise(question):
    return Comprehension(None).comprendre(question).requete


def test_n_tilde_ng_n_est_plus_efface():
    # « kuraŋ » devenait « kura » (ŋ sans équivalent ASCII) : le mot n'était plus reconnu
    assert texte_normalise("kuraŋ") == "kurang"
    assert "kurang" in index().requete("Ñaata kër ñoo am kuraŋ ci Senegaal ?")


def test_ker_menages_et_kurang_electricite():
    r = _comprise("Ñaata kër ñoo am kuraŋ ci Senegaal ?")
    assert r.indicateur == "asongtc" and r.zones == ["SN"]  # ménages et éclairage, pas le robinet


def test_gena_nakk_kurang_le_plus_faible_acces():
    r = _comprise("Ban diiwaan moo gëna ñàkk kuraŋ ?")
    assert (r.indicateur, r.intention, r.ordre) == ("asongtc", "classement", "asc")  # pas la pauvreté


@pytest.mark.parametrize("question, indicateur", [
    ("Ban diiwaan moo gëna ñàkk ?", "jcvcajc.taux-de-pauvrete"),  # le plus pauvre : la pauvreté la plus élevée
    ("Ban diiwaan moo gëna ñàkk liggéey ?", "dwibrlf"),  # le chômage le plus élevé
])
def test_gena_nakk_seul_ou_liggeey_reste_le_plus_eleve(question, indicateur):
    r = _comprise(question)
    assert (r.indicateur, r.intention, r.ordre) == (indicateur, "classement", "desc")


@pytest.mark.parametrize("question", [
    "Ñaata kër yu dëkk ci gox-goxaan yi ñoo am mbëj ?", "Ñaata kër ci kaw gi ñoo am kuraŋ ?",
    "Ñaata kër ci àll bi ñoo am kuraŋ ?",
])
def test_milieu_rural_en_wolof(question):  # KBD, 07/10 : gox-goxaan, kaw gi, àll bi = rural
    assert desagregation_citee(question) == {"milieu": "rural"}


def test_kaw_seul_n_est_pas_le_rural():
    assert "milieu" not in desagregation_citee("Ban diiwaan moo ëpp ci kaw ?")


@pytest.mark.parametrize("question, indicateur", [
    # « nit » n'est que dans le libellé wolof des prisons : sans « askan », les détenus répondaient (07/10)
    ("Ñaata nit ñoo dëkk Kaolack ?", "pvswjnd"), ("Ñaata nit ñoo dëkk ci Senegaal ?", "pvswjnd"),
    ("Ñaata nit ñoo nekk kaso ci Senegaal ?", "ioxbglg.nombre-de-personnes-emprisonnees"),
    ("Ñata nitt nio nek kaso senegal ?", "ioxbglg.nombre-de-personnes-emprisonnees"),
])
def test_nit_dekk_population_et_kaso_prison(question, indicateur):
    assert _comprise(question).indicateur == indicateur
