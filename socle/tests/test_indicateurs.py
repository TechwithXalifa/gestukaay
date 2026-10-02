"""Référentiel des indicateurs (#3, décision 0005). Tourne en CI, sans le socle brut."""

import csv
import json
from pathlib import Path

import pytest
from gestukaay_socle.indicateurs import (
    COLONNES,
    FICHIER,
    PRIORITES,
    VERIFICATIONS,
    codes,
    dimension_indicateur,
    domaines,
    indicateurs,
    libelle,
    nom_du_jeu,
)
from gestukaay_socle.zones import normaliser

JEU = Path(__file__).parents[2] / "mesure" / "jeu_de_test" / "questions.csv"
with open(JEU, encoding="utf-8-sig", newline="") as _f:
    QUESTIONS = {q["id"]: q for q in csv.DictReader(_f, delimiter=";")}


def test_colonnes_dans_l_ordre():
    with FICHIER.open(encoding="utf-8") as f:
        assert tuple(next(csv.reader(f, delimiter=";"))) == COLONNES


def test_referentiel_coherent():
    ind = indicateurs()
    domaines_valides = {d.domaine for d in domaines().values() if d.domaine}
    assert len(ind) > 3000  # tout le socle (décision 0005)
    for x in ind.values():
        assert x.code.startswith(x.dataset_id), x.code
        assert x.verification in VERIFICATIONS, x.code
        assert x.priorite in PRIORITES, x.code
        assert x.domaine in domaines_valides or x.verification == "ecarte", x.code
        assert (x.priorite == "P1") == bool(x.questions_test), x.code
        assert x.libelle_fr and x.nb_valeurs > 0, x.code
        # wolof : jamais sans statut, et jamais un statut sans libellé
        assert bool(x.libelle_wo) == (x.statut_wo in ("a_valider", "valide")), x.code
        assert bool(x.valeur_portail) == bool(x.dimension_indicateur), x.code
        assert x.periode_debut <= x.periode_fin, x.code


def test_domaines_doublons_fusionnes():
    d = domaines()
    assert d["Chômage"].domaine == d["Travail et emploi"].domaine
    assert d["Prix"].domaine == d["Prix à la consommation"].domaine
    assert d["PIB"].domaine == d["Comptes nationaux"].domaine
    assert d["Métadonnées"].domaine == ""
    # les 6 domaines des questions types du cahier (priorité P2)
    assert {x.domaine for x in d.values() if x.questions_types} == {
        "Démographie", "Emploi et chômage", "Prix", "Éducation", "Pauvreté", "Santé"}


@pytest.mark.parametrize("q", QUESTIONS.values(), ids=lambda q: q["id"])
def test_chaque_question_couverte_ou_hors_perimetre(q):
    """Fini quand (#3) : chaque question du jeu est couverte ou marquée hors périmètre."""
    utilisees = [x for x in indicateurs().values() if q["id"] in x.questions_test]
    if q["issue_attendue"] == "aucune":
        assert not utilisees and q["motif"]
        return
    assert utilisees, f"{q['id']} : aucun indicateur"
    filtres = json.loads(q["filtres"])
    ik = dimension_indicateur(filtres)
    for x in utilisees:
        assert x.dataset_id == q["dataset_id"]
        if ik:
            assert normaliser(filtres[ik]) in {normaliser(v) for v in x.valeur_portail.split("|")}


def test_questions_test_existent():
    for x in indicateurs().values():
        for q in x.questions_test:
            assert q in QUESTIONS, f"{x.code} : question inconnue {q}"


def test_unite_dans_l_identite():
    """Deux unités d'un même indicateur = deux codes (comptes nationaux courants / constants)."""
    c = codes([("uipcgjd", "total", "En milliards de francs CFA courants"),
               ("uipcgjd", "total", "En milliards de francs CFA aux prix constants de 1999"),
               ("dwibrlf", "", "%")])
    assert c[("uipcgjd", "total", "En milliards de francs CFA courants")] == "uipcgjd.total~courants"
    assert c[("uipcgjd", "total", "En milliards de francs CFA aux prix constants de 1999")] == \
        "uipcgjd.total~aux-prix-constants-de-1999"
    assert c[("dwibrlf", "", "%")] == "dwibrlf"


def test_codes_stables_et_uniques_meme_tronques():
    long_ = "pourcentage de femmes de 15 49 ans actuellement en union ou en rupture dunion qui ont subi des "
    ids = [("ahjjzgc", long_ + "violences physiques", ""), ("ahjjzgc", long_ + "violences sexuelles", "")]
    c = codes(ids)
    assert len(set(c.values())) == 2
    assert codes(list(reversed(ids))) == c  # indépendant de l'ordre


def test_libelles():
    assert nom_du_jeu("12.3_Taux de chômage (par région, sexe et âge)") == "Taux de chômage (par région, sexe et âge)"
    assert nom_du_jeu("18.3-b_Résultats des campagnes") == "Résultats des campagnes"
    assert libelle("11.1_Produit intérieur brut", "Total") == "Produit intérieur brut — Total"
    assert libelle("x", "Taux  de pauvreté") == "Taux de pauvreté"
    assert dimension_indicateur({"sexe": "Total", "indicateurs-vaccination": "x"}) == "indicateurs-vaccination"
    assert dimension_indicateur({"indicator": "Salaire"}) == "indicator"
    assert dimension_indicateur({"régions": "Dakar"}) is None
