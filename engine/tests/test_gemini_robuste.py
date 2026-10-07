"""Passe Gemini du 07/10 (#21) : doublons choisis par le LLM (A1, A2), précisions inventées (B)."""

import pytest
from gestukaay_contracts.models import Periode, RequeteStructuree
from gestukaay_engine.candidats import index, periodes_citees, zones_citees
from gestukaay_engine.comprehension import (
    SYSTEME,
    Comprehension,
    K,
    _verifie_en_tete,
    couvrant,
    projection,
)
from gestukaay_engine.moteur import _sans_precision_inventee
from gestukaay_engine.resolution import Introuvable
from gestukaay_socle.zones import zones


def _candidats(question):
    zs = zones_citees(question)
    niv = {zones()[z].niveau for z in zs if z != "SN"}
    return couvrant(index().chercher(question, 4 * K, niv), niv)[:K], zs, periodes_citees(question)


@pytest.mark.parametrize("question, choix_llm, attendu", [
    # la projection de 2013 au lieu du recensement (FR-023), le jeu arrêté en 2023 au lieu de 2025 (FR-028)
    ("Combien de femmes vivent dans la région de Matam ?", "uzptmtd", "pvswjnd"),
    ("Quel est le pourcentage de filles parmi les élèves du secondaire au Sénégal ?",
     "qqjyoh.pourcentage-de-filles-dans-les-effectifs", "ervtjfc.pourcentage-de-filles-dans-les-effectifs"),
])
def test_a2_le_verifie_en_tete_remplace_un_doublon(question, choix_llm, attendu):
    cands, zs, ps = _candidats(question)
    assert _verifie_en_tete(choix_llm, cands, zs, ps) == attendu


def test_a2_ne_touche_pas_une_annee_hors_du_verifie():
    # « en 2040 » : le RGPH-5 (2023) ne couvre pas l'année ; le choix du LLM (projection) reste
    cands, zs, ps = _candidats("Quelle sera la population du Sénégal en 2040 ?")
    assert _verifie_en_tete("aykimoe", cands, zs, ps) == "aykimoe"


def test_a2_ne_touche_pas_un_choix_verifie():
    cands, zs, ps = _candidats("Combien coûte le mil au détail ?")
    assert _verifie_en_tete("sbsryhc", cands, zs, ps) == "sbsryhc"  # vérifié lui aussi : le LLM décide


def test_a1_projections_marquees_et_consigne():
    assert projection("uzptmtd") == "toutes" and projection("pvswjnd") is None
    assert "OBSERVÉE" in SYSTEME and "la plus récente" not in SYSTEME
    cands, zs, ps = _candidats("Combien de femmes vivent dans la région de Matam ?")
    message = Comprehension._message("femmes Matam", zs, ps, cands, None)
    assert any("Population du Sénégal par région, age et sexe - 2023 — projection" in ligne
               for ligne in message.splitlines())  # uzptmtd marqué


def _req(desag):
    return RequeteStructuree(intention="valeur", indicateur="wdvdnub.proportion-denfants-de-12-a-23-mois",
                             zones=["SN-TC"], periode=Periode(type="derniere"), desagregation=desag, confiance=0.9)


def test_b_precision_inventee_retiree():
    r = Introuvable("desagregation_absente", "sexe = femmes : non publié pour cet indicateur", dimension_absente="sexe")
    sans = _sans_precision_inventee(r, _req({"sexe": "femmes"}), "Proportion xale yi am vaccins yeup tamba")
    assert sans is not None and sans.desagregation is None


def test_b_precision_citee_reste_stricte():
    # « des filles » est dans la question : décision 0011, pas de chiffre pour tous à la place
    r = Introuvable("desagregation_absente", "sexe = femmes : non publié pour cet indicateur", dimension_absente="sexe")
    assert _sans_precision_inventee(r, _req({"sexe": "femmes"}), "Vaccination des filles à Tambacounda") is None


def test_b_categorie_ambigue_non_touchee():
    # la dimension existe (choix proposés) : ce n'est pas une précision inventée
    r = Introuvable("desagregation_absente", "sexe = femmes", choix={"sexe": ["Masculin", "Féminin"]})
    assert _sans_precision_inventee(r, _req({"sexe": "femmes"}), "Proportion xale yi am vaccins yeup tamba") is None


def test_b_ne_depend_pas_du_texte_du_message():
    # revue de SAN : le cas est repéré par un champ de la résolution, pas par la formulation du détail
    r = Introuvable("desagregation_absente", "un tout autre libellé", dimension_absente="sexe")
    assert _sans_precision_inventee(r, _req({"sexe": "femmes"}), "Proportion xale yi am vaccins yeup tamba") is not None


@pytest.mark.parametrize("question", [
    "Quelle est la recette touristique en 2022 ?", "Recette totale des musées en 2020",
    "Combien de terrains de foot à Dakar ?", "Combien de voix pour le président en 2024 ?",
])
def test_hors_sujet_ne_capture_pas_une_question_de_chiffre(question):  # revue de SAN sur #147
    from gestukaay_engine.conversation import regles
    assert regles(question) is None


def test_regles_ne_contredisent_pas_un_llm_qui_a_trouve_un_indicateur():
    from gestukaay_engine.comprehension import SortieLLM

    class Llm:  # le LLM trouve l'indicateur et ne voit pas de conversation
        def structurer(self, systeme, message, modele):
            return SortieLLM(intention="valeur", candidat=1, confiance=0.9), None

    c = Comprehension(Llm()).comprendre("Bonjour Gëstukaay, la population de Thiès")
    assert c.conversation is None and c.requete.indicateur


def test_a2_ne_ramene_pas_une_donnee_plus_ancienne_sans_annee():
    # revue de SAN : sans année, un choix observé qui va plus loin dans le temps n'est pas remplacé
    from gestukaay_engine.candidats import Candidat
    from gestukaay_socle.indicateurs import indicateurs
    I = indicateurs()
    paire = next((v, n) for v in I.values() if v.verification == "verifie" and v.niveaux_zone
                 for n in I.values() if n.verification != "verifie" and n.domaine == v.domaine
                 and n.periode_fin[:4] > v.periode_fin[:4] and projection(n.dataset_id) is None)
    v, n = paire
    assert _verifie_en_tete(n.code, [Candidat(v, 10.0), Candidat(n, 5.0)], [], []) == n.code

