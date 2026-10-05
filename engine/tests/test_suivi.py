"""Suivi sur 3 échanges (#15, décision 0021). Règles locales et LLM simulé : aucun appel réseau."""

import pytest
from gestukaay_contracts.models import AskRequest, Periode, RequeteStructuree
from gestukaay_engine.comprehension import Comprehension, _suivi
from test_comprehension import client, sortie
from test_moteur import MOTEUR


def req(indicateur="dwibrlf", zones=("SN-DK",), periode=None, fin=None, intention="valeur", ordre="desc",
        **desag):
    p = Periode(type="derniere") if periode is None else Periode(type="annee", valeur=periode, fin=fin)
    return RequeteStructuree(intention=intention, indicateur=indicateur, zones=list(zones), periode=p,
                             desagregation=desag or None, ordre=ordre, confiance=0.9)


REGLES = Comprehension(None)


def test_la_periode_explicite_est_gardee():
    """EF-09 : « Et Thiès ? » après « Chômage à Dakar en 2019 » -> Thiès en 2019, pas la dernière année."""
    r = REGLES.comprendre("Et Thiès ?", [req(periode="2019")]).requete
    assert (r.indicateur, r.zones, r.periode.valeur) == ("dwibrlf", ["SN-TH"], "2019")


def test_la_periode_citee_remplace():
    r = REGLES.comprendre("Et en 2025 ?", [req(periode="2019")]).requete
    assert (r.zones, r.periode.valeur) == (["SN-DK"], "2025")


def test_la_desagregation_est_gardee_pour_le_meme_indicateur():
    r = REGLES.comprendre("Et Dakar ?", [req("pvswjnd", ["SN-TH"], "2023", sexe="femmes")]).requete
    assert (r.zones, r.periode.valeur, r.desagregation) == (["SN-DK"], "2023", {"sexe": "femmes"})


def test_comparaison_de_zones_gardee():
    avant = req(zones=("SN-DK", "SN-TH"), periode="2024", intention="comparaison")
    r = REGLES.comprendre("Et en 2025 ?", [avant]).requete
    assert (r.intention, r.zones, r.periode.valeur) == ("comparaison", ["SN-DK", "SN-TH"], "2025")


def test_evolution_gardee_pour_une_autre_zone():
    avant = req("jcvcajc.taux-de-pauvrete", ("SN",), "2011", fin="2022", intention="comparaison")
    r = REGLES.comprendre("Et Dakar ?", [avant]).requete
    assert (r.intention, r.zones, r.periode.valeur, r.periode.fin) == ("comparaison", ["SN-DK"], "2011", "2022")


def test_classement_garde_son_sens():
    avant = req(zones=(), periode="2025", intention="classement", ordre="asc")
    r = REGLES.comprendre("Et en 2024 ?", [avant]).requete
    assert (r.intention, r.ordre, r.periode.valeur) == ("classement", "asc", "2024")


def test_dernier_echange_compris_parmi_les_trois():
    """Thiès, puis une incompréhension et un hors périmètre : « et Kaolack ? » repart de Thiès."""
    perdu = RequeteStructuree(intention="hors_perimetre", confiance=0.1)
    contexte = [req("pvswjnd", ["SN-TH"], "2023"), None, perdu]
    r = REGLES.comprendre("Et Kaolack ?", contexte).requete
    assert (r.indicateur, r.zones, r.periode.valeur) == ("pvswjnd", ["SN-KL"], "2023")


def test_au_dela_de_trois_echanges_le_fil_est_perdu():
    perdu = RequeteStructuree(intention="hors_perimetre", confiance=0.1)
    contexte = [req("pvswjnd", ["SN-TH"], "2023"), perdu, perdu, perdu]
    assert REGLES.comprendre("Et Kaolack ?", contexte).requete.indicateur != "pvswjnd"


def test_le_llm_herite_aussi():
    r = Comprehension(client(sortie(candidat=1))).comprendre("Kaolack nak ?", [req("pvswjnd", ["SN-TH"], "2023")])
    assert (r.source, r.requete.indicateur, r.requete.zones, r.requete.periode.valeur) == \
        ("llm", "pvswjnd", ["SN-KL"], "2023")


@pytest.mark.parametrize("question", ["Et pour Kaolack ?", "Pour Kaolack ?", "Kaolack aussi ?",
                                      "Même chose pour Kaolack", "Kaolack nak ?", "Ak Kaolack ?",
                                      "Kaolack tamit ?"])
def test_marqueurs_de_suivi(question):
    assert _suivi(question)


@pytest.mark.parametrize("question", ["Combien d'habitants à Kaolack ?", "Chômage Dakar ak Thiès ?",
                                      "Quel est le taux de chômage à Kaolack aussi en 2019 ?"])
def test_pas_de_suivi(question):
    assert not _suivi(question)


def test_moteur_reel_suivi_bout_en_bout():
    avant = MOTEUR.repondre(AskRequest(question="Combien d'habitants à Thiès en 2023 ?")).reponse
    r = MOTEUR.repondre(AskRequest(question="Et pour Dakar ?"), [avant.requete]).reponse
    assert r.issue == "exacte" and [(x.zone.code, x.periode.valeur, x.valeur) for x in r.resultats] == \
        [("SN-DK", "2023", 4004426)]


@pytest.mark.parametrize("question", ["Kaolack nak?", "Kaolack aussi?", "Kaolack tamit?", "Et pour Kaolack?",
                                      "Ak Kaolack?", "Kaolack nak!"])
def test_marqueur_de_suivi_avec_ponctuation_collee(question):
    """Relecture de SAN (#123) : « Kaolack nak? », tapé ou sorti de la transcription, est un suivi."""
    assert _suivi(question)
    r = REGLES.comprendre(question, [req("pvswjnd", ["SN-TH"], "2023")]).requete
    assert (r.indicateur, r.zones, r.periode.valeur) == ("pvswjnd", ["SN-KL"], "2023")
