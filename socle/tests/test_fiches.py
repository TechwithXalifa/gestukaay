"""Fiches des jeux et des indicateurs (#7). Tourne en CI, sans le socle brut."""

from gestukaay_socle.fiches import decouper, jeux, nettoyer
from gestukaay_socle.indicateurs import indicateurs


def test_decouper_le_modele_des_annuaires():
    texte = ("\r\n1. Intitulé de l'indicateur\r\n\xa0Taux de chômage\r\n\xa02. Définition de l'indicateurIl évalue "
             "le poids des chômeurs.\xa0\r\n3. Type de données\r\nEnquête\r\n4. Opération\r\nEnquête nationale sur "
             "l'emploi au Sénégal (ENES)\r\n5. Méthode de calcul\xa0chômeurs/(population active)*100\r\n"
             "6. Observations sur la série NEANT")
    r = decouper(texte)
    assert r["intitule"] == "Taux de chômage"
    assert r["definition"] == "Il évalue le poids des chômeurs"
    assert r["operation"] == "Enquête nationale sur l'emploi au Sénégal (ENES)"
    assert r["methode"] == "chômeurs/(population active)*100"
    assert r["observations"] == ""  # « NEANT » du portail


def test_texte_libre_garde_tel_quel():
    assert decouper("<p>Ce jeu de donn&eacute;es montre les arriv&eacute;es</p>") == {
        "description": "Ce jeu de données montre les arrivées"}
    assert nettoyer("a\xa0 \r\n b") == "a b"


def test_chaque_indicateur_a_une_fiche_de_jeu():
    assert {x.dataset_id for x in indicateurs().values()} <= set(jeux())


def test_definitions_citees_jamais_redigees():
    """Décision #7 : une définition propre est un extrait exact du texte publié par le portail."""
    for x in indicateurs().values():
        if x.definition:
            j = jeux()[x.dataset_id]
            assert x.definition in j.definition or x.definition in j.description, x.code


def test_operation_des_annuaires():
    assert jeux()["dwibrlf"].operation == "Enquête nationale sur l'emploi au Sénégal (ENES)"
    assert "EHCVM" in jeux()["jcvcajc"].operation
