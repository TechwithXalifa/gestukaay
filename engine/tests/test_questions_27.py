"""410 questions sur les 27 indicateurs vérifiés (08/10) : évolutions, séries mensuelles, plus haut et plus bas
niveau, définitions. Socle synthétique et règles locales : tourne en CI, sans réseau."""

from datetime import date

import pytest
from gestukaay_contracts.models import AskRequest
from gestukaay_engine.candidats import (
    est_evolution,
    extremum,
    fenetre_annees,
    fenetre_periodes,
    periodes_citees,
)
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.conversation import regles as conversation
from gestukaay_engine.moteur import MoteurReel
from gestukaay_engine.socle import Observation, Socle, SourceJeu


def obs(ind, zone, periode, valeur, **dims):
    return Observation(id=f"{ind}-{zone}-{periode}-{valeur}-{dims}", indicateur=ind, zone=zone, zone_presumee=False,
                       periode=periode, desagregation=tuple(sorted(dims.items())), valeur=valeur, unite="",
                       echelle="1", source_id=ind.split(".")[0], nature="observee", base_projection="")


RIZ = "feujxob.riz-brise-ordinaire-au-detail"
SOURCES = {d: SourceJeu(d, "ANSD", "Agence nationale", f"Jeu {d}", date(2023, 10, 31), "", f"https://x/{d}")
           for d in ("feujxob", "ioxbglg", "elwxsmc", "sbsryhc")}
SOCLE = Socle([
    *[obs(RIZ, "SN-DK", f"{a}-{m:02d}", 280 + (a - 2016) * 5 + m, ) for a in (2016, 2019, 2025, 2026) for m in range(1, 13)
      if (a, m) <= (2026, 3)],
    *[obs("ioxbglg.nombre-de-personnes-emprisonnees", "SN", str(a), v) for a, v in
      ((2017, 9000), (2019, 10000), (2020, 10537), (2023, 12910), (2025, 15721))],
    *[obs("elwxsmc.indice-synthetique-de-fecondite", "SN", str(a), v, **{"tranche-d-âge": "15-49 ans"})
      for a, v in ((1986, 6.4), (2005, 5.3), (2010, 5.0), (2025, 4.2))],
    *[obs("sbsryhc", z, "2023", v, **{"type-de-céréales": c}) for z, v0 in (("SN-DK", 400), ("SN-KL", 340))
      for c, v in (("mil", v0), ("sorgho", v0 + 20), ("Mais", v0 - 30))],
], SOURCES, "test")
MOTEUR = MoteurReel(SOCLE, Comprehension(None))


def demander(q):
    return MOTEUR.repondre(AskRequest(question=q)).reponse


# --- lecture de la question ------------------------------------------------------------------------------

@pytest.mark.parametrize("question,periodes", [
    ("Le salaire moyen a-t-il augmenté entre le quatrième trimestre 2025 et le premier trimestre 2026 ?",
     ["2025-T4", "2026-T1"]),
    ("Le prix du riz a-t-il baissé entre février et mars 2026 ?", ["2026-02", "2026-03"]),
    ("Quel était le salaire moyen au premier trimestre 2026 ?", ["2026-T1"]),
    ("Le taux a-t-il progressé entre le premier et le deuxième trimestre 2023 ?", ["2023-T1", "2023-T2"]),
    ("Quel était le taux fin 2022 ?", ["2022"]),
])
def test_periodes_en_toutes_lettres(question, periodes):
    assert periodes_citees(question) == periodes


@pytest.mark.parametrize("question", [
    "Le nombre moyen d'enfants par femme diminue-t-il au Sénégal ?", "Comment le PIB a-t-il évolué ?",
    "Le nombre de personnes emprisonnées a-t-il augmenté après 2020 ?",
    "Comment la criminalité a-t-elle évolué au cours des dix dernières années ?",
    "Quelles sont les tendances de long terme de l'espérance de vie ?",
    "Comment le salaire moyen évolue-t-il d'un trimestre à l'autre ?",
])
def test_questions_d_evolution(question):
    assert est_evolution(question)


def test_pas_une_evolution():
    assert not est_evolution("Quel est le taux de chômage au Sénégal en 2025 ?")


def test_fenetres():
    assert fenetre_annees("au cours des dix dernières années") == 10
    assert fenetre_annees("sur près de quarante ans") == 40
    assert fenetre_periodes("au cours des douze derniers mois disponibles") == 12


def test_extremum():
    assert extremum("Quel mois a enregistré le plus d'arrivées de visiteurs en 2018 ?") == "max"
    assert extremum("À quelle période le riz était-il le moins cher depuis 2016 ?") == "min"
    assert extremum("Quelle région a le taux de pauvreté le plus élevé ?") is None  # un classement de régions


@pytest.mark.parametrize("question,attendu", [
    ("Quelle est la différence entre le taux brut et le taux net de scolarisation ?", "definition"),
    ("Que signifie un indice de Gini de 0,35 au Sénégal ?", "definition"),
    ("Comment expliquer un taux de pénétration supérieur à 100 % ?", "pourquoi"),
    ("Quelles sont les conséquences de l'urbanisation sur les besoins en logements ?", "pourquoi"),
    ("Quelle est la différence entre le chômage à Dakar et à Thiès en 2024 ?", None),  # des chiffres
])
def test_definitions_et_causes(question, attendu):
    assert conversation(question) == attendu


# --- réponses -----------------------------------------------------------------------------------------------

def test_evolution_donne_deux_periodes():
    r = demander("Le nombre moyen d'enfants par femme diminue-t-il au Sénégal ?")
    assert r.issue == "exacte" and [x.periode.valeur for x in r.resultats] == ["1986", "2025"]
    r = demander("Le nombre de personnes emprisonnées a-t-il augmenté après 2020 ?")
    assert [x.periode.valeur for x in r.resultats] == ["2020", "2025"]


def test_qu_il_y_a_vingt_ans_part_de_l_annee_publiee_la_plus_proche():
    r = demander("Le nombre moyen d'enfants par femme a-t-il baissé depuis 2006 ?")
    assert [x.periode.valeur for x in r.resultats] == ["2005", "2025"]


def test_annee_sur_serie_mensuelle_le_mois_est_propose():  # choix de KBD (08/10) : proposé, pas choisi pour lui
    r = demander("Combien coûtait un kilogramme de riz brisé ordinaire en 2019 ?")
    assert r.issue == "approchee" and "par mois" in r.reformulation
    assert [c.requete.periode.valeur for c in r.choix] == ["2019-12", "2019-11", "2019-10"]


def test_douze_derniers_mois():
    r = demander("Comment le prix du riz a-t-il évolué au cours des douze derniers mois disponibles ?")
    assert [x.periode.valeur for x in r.resultats] == ["2025-03", "2026-03"]


def test_plus_bas_niveau_de_la_serie():
    r = demander("À quelle période le riz brisé ordinaire était-il le moins cher depuis 2016 ?")
    assert r.issue == "exacte" and r.resultats[0].periode.valeur == "2016-01"
    assert r.explication.startswith("C'est le niveau le plus bas publié entre janvier 2016 et mars 2026.")


def test_cereales_locales_du_senegal_classement_des_regions():
    r = demander("Quel est le prix moyen des céréales locales au Sénégal ?")
    assert r.issue == "approchee"
    assert all(c.requete.intention == "classement" for c in r.choix)


def test_le_llm_ne_sert_pas_un_indicateur_non_verifie_hors_sujet():
    """« l'ensemble de la période » -> « Ensemble garçon » (un vêtement) : refusé, pas servi."""
    import json

    import httpx
    from gestukaay_engine.candidats import index
    from gestukaay_engine.llm import ClientLLM, Maillon

    q = "Quelle évolution des prix peut-on observer sur l'ensemble de la période 2015–2023 ?"
    cands = index().chercher(q, 60)
    n = next(i for i, c in enumerate(cands[:15], 1) if c.indicateur.code == "feujxob.ensemble-garcon") \
        if any(c.indicateur.code == "feujxob.ensemble-garcon" for c in cands[:15]) else None
    if n is None:
        pytest.skip("candidat absent de la liste")
    sortie = {"intention": "comparaison", "candidat": n, "periode_type": "derniere", "periode_valeur": None,
              "confiance": 0.9}
    client = ClientLLM([Maillon(nom="p", fournisseur="openai_compatible", modele="x", cle="k")],
                       transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
                           "choices": [{"message": {"content": json.dumps(sortie)}, "finish_reason": "stop"}]})))
    assert Comprehension(client).comprendre(q).requete.indicateur is None


def test_modalites_sans_ligne_commune_pas_de_plantage():
    """Deux dimensions fixées une à une sans ligne commune : Introuvable, jamais IndexError (08/10)."""
    from gestukaay_contracts.models import RequeteStructuree
    from gestukaay_engine.resolution import Introuvable, resoudre
    socle = Socle([obs("feujxob.riz-brise-ordinaire-au-detail", "SN", "2020", 1, a="Total", b="x"),
                   obs("feujxob.riz-brise-ordinaire-au-detail", "SN", "2020", 2, a="y", b="Total")], SOURCES, "t")
    r = resoudre(socle, RequeteStructuree(intention="valeur", indicateur=RIZ, zones=["SN"], confiance=1), "fr")
    assert isinstance(r, Introuvable)
