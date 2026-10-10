"""Issues de SAN du 09/10 (revue de #220 et #222, test du bot) : #232, #236, #237, #238, #239, #241, #242."""

from types import SimpleNamespace

import pytest
from gestukaay_engine.candidats import mesure_inverse, sans_emploi
from gestukaay_engine.conversation import domaine_demande
from gestukaay_engine.moteur import _annees_non_servies, saisie_propre
from gestukaay_socle.indicateurs import indicateurs


@pytest.mark.parametrize("question", ["Quelle est la dépense des ménages en électricité ?",
                                      "Combien dépensent les ménages pour la santé à Dakar ?",
                                      "Combien dépensent les ménages d'eau ?"])
def test_depense_d_un_poste_jamais_reecrite_en_consommation_totale(question):  # #236
    assert "consommation moyenne par tête" not in sans_emploi(question)


@pytest.mark.parametrize("question", ["Combien dépensent les ménages en moyenne ?",
                                      "Combien dépensent les ménages en moyenne à Dakar ?",
                                      "Combien dépensent les ménages en 2022 ?"])
def test_depense_moyenne_des_menages_toujours_reecrite(question):  # #209 reste vrai
    assert "consommation moyenne par tête" in sans_emploi(question)


@pytest.mark.parametrize("question", ["Quels sont les chiffres de la population ?",
                                      "Quelles sont les statistiques de la pauvreté ?"])
def test_les_chiffres_de_x_demandent_x_pas_la_liste_du_domaine(question):  # #237
    assert domaine_demande(question) is None


def test_les_donnees_sur_un_domaine_restent_une_liste():  # #216 reste vrai
    assert domaine_demande("Quelles données as-tu sur l'agriculture ?") == "Agriculture"
    assert domaine_demande("Quelles données de la santé ?") == "Santé"


def test_negation_sur_la_population_ne_refuse_pas_la_mesure():  # #238
    assert not mesure_inverse("dwibrlf", "Taux de chômage des personnes qui ne sont pas diplômées")


@pytest.mark.parametrize("code, question", [
    ("asongtc", "Combien de ménages n'ont pas accès à l'électricité ?"),  # #206 : jamais la part qui A accès
    ("ahjjzgc.taux-dacces-des-menages-a-une-source-deau", "Part des ménages qui n'ont pas accès à l'eau potable"),
    ("ervtjfc.taux-brut-de-scolarisation", "Taux des enfants qui ne sont pas scolarisés"),
])
def test_negation_sur_la_mesure_reste_inverse(code, question):
    assert mesure_inverse(code, question)


def test_aucun_libelle_de_variation_des_prix_sans_inflation_ni_glissement():  # #239, socle 2026.10.1
    import re
    prix = [i for i in indicateurs().values() if re.search(r"\b(ihpc|prix a la consommation|indice harmonise)",
                                                          i.libelle_fr.lower().replace("à", "a"))]
    variation = [i.code for i in prix if re.search(r"variation|croissance|evolution", i.libelle_fr.lower())]
    # oabkope : le taux d'inflation annuel 1980-2014 (affiché en %). Le servir ou non pour « l'inflation » (une
    # donnée de 2014) est une décision de KBD (#239) : aujourd'hui, refus. Un nouveau libellé : élargir _INFLATION.
    assert set(variation) <= {"oabkope.evolution-ihpc"}
    assert indicateurs()["oabkope.evolution-ihpc"].unite_affichee == "%"


def test_tirets_et_comparaisons_gardes_balises_retirees():  # #241
    assert saisie_propre("Pauvreté entre 2011–2022") == "Pauvreté entre 2011-2022"
    assert saisie_propre("taux < 5 % et > 2 %") == "taux < 5 % et > 2 %"
    assert saisie_propre("<b>Combien d'habitants</b> à Thiès ?") == "Combien d'habitants à Thiès ?"


def _res(*annees):
    return [SimpleNamespace(periode=SimpleNamespace(valeur=a)) for a in annees]


def test_annee_citee_jamais_perdue_en_silence():  # #242
    q = "Taux de pauvreté à Dakar en 2011, 2019 et 2022"
    assert _annees_non_servies(q, _res("2011", "2019")) == ["2022"]
    assert _annees_non_servies("Taux de pauvreté à Dakar en 2011 et 2022", _res("2011")) == []  # deux : rien à dire


def test_population_de_l_enquete_emploi_dit_ce_qu_elle_est():  # #232
    assert "enquête emploi" in indicateurs()["puummg.population-totale"].libelle_fr
