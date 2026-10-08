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


def test_gox_goxaan_milieu_rural():
    assert desagregation_citee("Ñaata kër yu dëkk ci gox-goxaan yi ñoo am mbëj ?") == {"milieu": "rural"}


@pytest.mark.parametrize("question, indicateur", [
    # « nit » n'est que dans le libellé wolof des prisons : sans « askan », les détenus répondaient (07/10)
    ("Ñaata nit ñoo dëkk Kaolack ?", "pvswjnd"), ("Ñaata nit ñoo dëkk ci Senegaal ?", "pvswjnd"),
    ("Ñaata nit ñoo nekk kaso ci Senegaal ?", "ioxbglg.nombre-de-personnes-emprisonnees"),
    ("Ñata nitt nio nek kaso senegal ?", "ioxbglg.nombre-de-personnes-emprisonnees"),
])
def test_nit_dekk_population_et_kaso_prison(question, indicateur):
    assert _comprise(question).indicateur == indicateur


def test_jang_scolarisation():  # KBD, 07/10 (remarque de SAN sur #138) : jàng = étudier, pas le retard de croissance
    assert _comprise("Ñaata xale ñoo jàng ci Kolda ?").indicateur == "ervtjfc.taux-brut-de-scolarisation"


@pytest.mark.parametrize("question", ["Combien d'écoles au Sénégal ?", "ñaata ekool ñoo nekk ci senegaal",
                                      "ñaata lekool ñoo nekk ci senegaal"])
def test_ecole_n_est_pas_le_taux_de_scolarisation(question):  # ekool : KBD, 08/10 ; donnait 84,7 %
    assert "nombre" in _comprise(question).indicateur and "ecoles" in _comprise(question).indicateur


@pytest.mark.parametrize("question, periodes", [  # formes de KBD, questions du 08/10
    ("Ñaata la kiloy ceeb doon jar ci weeru mars atum 2026 ?", ["2026-03"]),
    ("Naka la njëg yi soppikoo la ko dale weeru samwiye atum 2000 ?", ["2000-01"]),
    ("IPC ci weeru sulet atum 2026", ["2026-07"]),
    ("ci ñaareelu ñetti weer yi ci atum 2023", ["2023-T2"]),
    ("diggante ñetti weer yu mujj yu 2025 ak ñetti weer yu njëkk yu 2026", ["2025-T4", "2026-T1"]),
])
def test_mois_et_trimestres_en_wolof(question, periodes):
    from gestukaay_engine.candidats import periodes_citees
    from gestukaay_engine.nombres import en_chiffres
    assert periodes_citees(question) == periodes
    assert periodes_citees(en_chiffres(question)) == periodes  # « ñetti » converti en « 3 » avant (#153)


def test_glossaire_wolof_dans_la_consigne():
    from gestukaay_engine.comprehension import SYSTEME
    assert "yamadi" in SYSTEME and "deeg xale yi" in SYSTEME and "ñakkug xale yi" in SYSTEME
    assert SYNONYMES["yamadi"] == ("gini",) and SYNONYMES["deeg"] == ("mortalite",)


def test_dekk_yi_all_bi_milieux_et_urbanisation():  # « ñoo dëkk ci dëkk yi » / « ci all bi » (KBD, 08/10)
    from gestukaay_engine.resolution import portee_par_indicateur
    from gestukaay_socle.indicateurs import indicateurs
    assert desagregation_citee("Ñata senegale ñoo dëkk ba tay ci all bi ?") == {"milieu": "rural"}
    assert desagregation_citee("Ñata ci téeméer ci askanu Senegaal ñoo dëkk ci dëkk yi ?") == {"milieu": "urbain"}
    assert desagregation_citee("Ñata nit ñoo dëkk Ndakaaru ?") == {}
    urb = indicateurs()["rfegvpb.taux-durbanisation"]
    assert portee_par_indicateur(urb, "urbain") and not portee_par_indicateur(urb, "rural")  # jamais 100 - x


def test_garde_fou_ne_compte_que_les_mots_ecrits():  # « dëkk » apportait « askan » : la population remplaçait
    from gestukaay_engine.comprehension import (
        _hors_sujet,  # l'urbanisation choisie par le LLM (08/10)
    )
    q = "Ñata senegale ñoo dëkk ba tay ci all bi ?"
    assert _hors_sujet("rfegvpb.taux-durbanisation", index().chercher(q, 15), q) == "rfegvpb.taux-durbanisation"
