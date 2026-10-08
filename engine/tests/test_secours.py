"""Recette du 08/10 : le secours par règles (35 % des questions quand la chaîne LLM tardait) servait un chiffre
vrai pour une autre question. Règles seules, socle synthétique : tourne en CI, sans réseau."""

from datetime import date

import pytest
from gestukaay_contracts.models import AskRequest, RequeteStructuree
from gestukaay_engine.candidats import (
    deux_sexes,
    index,
    lieux_inconnus,
    periodes_citees,
    zones_citees,
)
from gestukaay_engine.comprehension import Comprehension, _intention_de_la_question, couvert
from gestukaay_engine.moteur import MoteurReel
from gestukaay_engine.resolution import ANNEE_EN_COURS
from gestukaay_engine.socle import Observation, Socle, SourceJeu


def comprise(question, contexte=None):
    return Comprehension(None).comprendre(question, contexte)


@pytest.mark.parametrize("question", [
    "Quel est le salaire du président de la République ?",  # avant : le salaire moyen
    "Quelle est la dette publique du Sénégal ?",  # avant : les dépenses d'éducation « hors service de la dette »
    "Combien de voitures électriques au Sénégal ?",  # avant : un indice de location de voitures
    "Quel est le PIB par habitant du Sénégal ?",  # avant : le PIB total
    "Calcule la densité de population de Dakar",  # avant : la population de Dakar
    "Tu es nul",  # avant : la population carcérale de 2016
])
def test_secours_ne_sert_pas_un_chiffre_pour_une_autre_question(question):
    c = comprise(question)
    assert c.requete.indicateur is None and c.requete.intention == "hors_perimetre"


@pytest.mark.parametrize("question,indicateur", [
    ("Combien d'habitants à Thiès ?", "pvswjnd"),
    ("combien dhabitant a thies", "pvswjnd"),  # apostrophe oubliée
    ("c koi le taux de pauvreté a kolda svp", "jcvcajc.taux-de-pauvrete"),
    ("Bonjour, je voudrais savoir combien il y a d'habitants à Louga s'il vous plaît", "pvswjnd"),
    ("Les inégalités au Sénégal", "qjyrtof.gini"),
    ("Quelle part des ménages ruraux a un robinet dans le logement ou la concession ?",
     "kdtstle.robinet-dans-logement-concession"),
    ("Combien de personnes sont au chômage au Sénégal ?", "muhgux.population-au-chomage"),  # nombre (0024)
    ("Taux scolarisation primaire filles academie louga", "ervtjfc.taux-brut-de-scolarisation"),  # pas la part
])
def test_secours_garde_les_bonnes_reponses(question, indicateur):
    assert comprise(question).requete.indicateur == indicateur


def test_couverture_mots_qui_ne_disent_pas_quoi_mesurer():
    assert couvert("pvswjnd", "Combien d'habitants à Saint-Louis ?")
    assert not couvert("muhgux.salaire-moyen-mensuel", "Quel est le salaire du président ?")


def test_lieux_hors_senegal_jamais_le_senegal():
    assert lieux_inconnus("Population de Paris") == ["Paris"]
    assert lieux_inconnus("Population du Fouta") == ["Fouta"]
    assert lieux_inconnus("Combien d'habitants dans le monde ?") == ["monde"]
    for q in ("Combien d'habitants à Thiès ? Merci", "Quel est le PIB du Sénégal ?", "Taux de chômage selon l'ANSD",
              "Combien de touristes français en 2018 ?", "Quelle est la population de Saint-Louis ?"):
        assert lieux_inconnus(q) == [], q


def test_annees_dites_sans_chiffre():
    assert periodes_citees("Taux de chômage l'année dernière") == [str(ANNEE_EN_COURS - 1)]
    assert periodes_citees("Quel sera le taux de chômage l'année prochaine ?") == [str(ANNEE_EN_COURS + 1)]
    assert periodes_citees("Captures de poisson il y a 5 ans") == [str(ANNEE_EN_COURS - 5)]
    assert periodes_citees("Population en 2023") == ["2023"]


def test_suivi_precision_seule_garde_l_indicateur():
    precedente = RequeteStructuree(intention="valeur", indicateur="dwibrlf", zones=["SN"],
                                   periode={"type": "annee", "valeur": "2019"}, confiance=0.9)
    r = comprise("Et pour les femmes ?", [precedente]).requete
    assert r.indicateur == "dwibrlf" and r.desagregation == {"sexe": "femmes"}  # pas les femmes au gouvernement


def test_toutes_les_regions_est_un_classement():
    assert comprise("Compare la population de toutes les régions").requete.intention == "classement"
    assert comprise("Taux de pauvreté par région").requete.intention == "classement"


def test_le_llm_ne_classe_pas_quand_la_question_ne_cite_que_le_senegal():
    req = RequeteStructuree(intention="classement", indicateur="dwibrlf", zones=[], confiance=0.9)
    q = "Ñi amul ligéey ci Senegaal ?"
    assert _intention_de_la_question(req, q, zones_citees(q)).intention == "valeur"  # WO-002
    q = "Quelle région a le taux de chômage le plus élevé ?"
    assert _intention_de_la_question(req, q, zones_citees(q)).intention == "classement"


def test_deux_sexes():
    assert deux_sexes("Différence de taux de chômage entre hommes et femmes")
    assert not deux_sexes("Le taux de chômage des femmes")


# --- de bout en bout, socle synthétique ------------------------------------------------

def obs(ind, zone, periode, valeur, **dims):
    return Observation(id=f"{ind}-{zone}-{periode}-{valeur}-{dims}", indicateur=ind, zone=zone, zone_presumee=False,
                       periode=periode, desagregation=tuple(sorted(dims.items())), valeur=valeur, unite="",
                       echelle="1", source_id=ind.split(".")[0], nature="observee", base_projection="")


SOURCES = {d: SourceJeu(d, "ANSD", "Agence nationale", f"Jeu {d}", date(2023, 10, 31), "", f"https://x/{d}")
           for d in ("pvswjnd", "dwibrlf")}
SOCLE = Socle([
    obs("pvswjnd", "SN", "2023", 18126390, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-DK", "2023", 4004426, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-TH", "2023", 2463677, sexe="Total", age="Total"),
    obs("dwibrlf", "SN", "2015", 14.5, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN", "2024", 21.6, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN", "2025", 20.4, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN", "2025", 34.0, sexe="Femme", âge="TOTAL"),
    obs("dwibrlf", "SN", "2025", 11.0, sexe="Homme", âge="TOTAL"),
], SOURCES, "test")
MOTEUR = MoteurReel(SOCLE, Comprehension(None))


def demander(question):
    return MOTEUR.repondre(AskRequest(question=question)).reponse


@pytest.mark.parametrize("question", ["Population de Paris", "Combien d'habitants dans le monde ?",
                                      "Population du Fouta"])
def test_jamais_le_senegal_pour_un_lieu_hors_referentiel(question):
    r = demander(question)
    assert r.issue != "exacte"


def test_l_annee_prochaine_est_une_projection():
    r = demander("Quel sera le taux de chômage l'année prochaine ?")
    assert r.issue == "aucune" and r.motif == "projection"


def test_depuis_une_annee_donne_l_evolution_jusqu_a_la_derniere():
    r = demander("Évolution du taux de chômage depuis 2015")
    assert r.issue == "exacte" and [x.periode.valeur for x in r.resultats] == ["2015", "2025"]


def test_hommes_et_femmes_pas_encore_disponible_plutot_que_les_femmes_seules():
    r = demander("Différence de taux de chômage entre hommes et femmes")
    assert r.issue == "aucune" and r.motif == "non_disponible"


def test_index_charge():
    assert index().idf  # le garde-fou s'appuie sur le vocabulaire du référentiel


def test_ratio_un_par_de_ventilation_n_est_pas_un_ratio_publie():  # revue de SAN sur #162
    from gestukaay_engine.candidats import ratio_non_publie
    # « … lits par Hôpitaux, … par région » : le nombre de lits n'est pas un ratio pour 10 000 habitants
    assert ratio_non_publie("mksvmnc.hopitaux", "Combien de lits d'hôpital pour 10 000 habitants ?")
    assert ratio_non_publie("uzptmtd", "Quelle est la densité de population de Dakar ?")  # « par région, age et sexe »
    assert not ratio_non_publie("smcofug.quotient-de-mortalite-infanto-juvenile",
                                "Mortalité des moins de 5 ans pour 1 000 naissances")  # ratio publié


def test_suivi_nouvel_indicateur_passe_le_garde_fou():  # revue de SAN sur #162
    precedente = RequeteStructuree(intention="valeur", indicateur="dwibrlf", zones=["SN"],
                                   periode={"type": "derniere"}, confiance=0.9)
    r = comprise("Et le salaire du président ?", [precedente]).requete
    assert r.indicateur is None and r.intention == "hors_perimetre"  # ni le chômage ni le salaire moyen (muhgux)
