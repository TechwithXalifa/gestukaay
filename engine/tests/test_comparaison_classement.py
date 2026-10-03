"""Tests pour le chantier 2.6 : Comparaison et classement (#14, EF-07, US-04, EF-20, EF-26, EF-27).

Socle synthétique en mémoire : tourne en CI sans socle extrait brut.
Zéro chiffre inventé : chaque valeur testée correspond aux données vérifiées.
"""

from datetime import date

from gestukaay_contracts.models import Periode, RequeteStructuree
from gestukaay_engine.candidats import index
from gestukaay_engine.comprehension import regles
from gestukaay_engine.gabarits import comparaison, explication
from gestukaay_engine.resolution import Resolution, resoudre
from gestukaay_engine.socle import Observation, Socle, SourceJeu
from gestukaay_socle.indicateurs import indicateurs


def obs(ind, zone, periode, valeur, nature="observee", base="", **dims):
    return Observation(
        id=f"{ind}-{zone}-{periode}-{valeur}",
        indicateur=ind,
        zone=zone,
        zone_presumee=False,
        periode=periode,
        desagregation=tuple(sorted(dims.items())),
        valeur=valeur,
        unite="%" if "taux" in ind or "chomage" in ind else "habitants" if "pvswjnd" in ind else "",
        echelle="1",
        source_id=ind.split(".")[0],
        nature=nature,
        base_projection=base,
    )


SOURCES = {
    d: SourceJeu(d, "ANSD", "ANSD", f"Enquête {d}", date(2023, 10, 31), "CC BY 4.0", f"https://x/{d}")
    for d in ("pvswjnd", "dwibrlf", "jcvcajc", "ervtjfc", "feujxob", "asongtc")
}

# 14 régions pour le chômage 2025 (FR-041)
CHOMAGE_2025 = {
    "SN-MT": 48.0, "SN-KL": 37.2, "SN-SE": 30.2, "SN-ZG": 29.2, "SN-SL": 23.9,
    "SN-FK": 23.4, "SN-KD": 23.0, "SN-TH": 22.7, "SN-KA": 22.5, "SN-LG": 16.4,
    "SN-DB": 14.2, "SN-DK": 13.2, "SN-KE": 8.8, "SN-TC": 5.0,
}

# 14 régions pour la pauvreté 2022 (FR-043)
PAUVRETE_2022 = {
    "SN-DK": 9.3, "SN-TH": 29.9, "SN-SL": 37.3, "SN-DB": 37.4, "SN-MT": 44.7,
    "SN-FK": 46.5, "SN-LG": 47.0, "SN-ZG": 48.3, "SN-KL": 49.6, "SN-KA": 58.2,
    "SN-KD": 62.5, "SN-TC": 62.8, "SN-SE": 64.4, "SN-KE": 65.7,
}

# 16 académies pour le taux brut de scolarisation 2025 (FR-040)
TBS_2025 = {
    "SN-IA-ZIGUINCHOR": 116.58, "SN-IA-KEDOUGOU": 109.83, "SN-IA-THIES": 104.69,
    "SN-IA-DAKAR": 101.16, "SN-IA-SEDHIOU": 100.07, "SN-IA-SAINT-LOUIS": 96.71,
    "SN-IA-PIKINE-GUEDIAWAYE": 95.0, "SN-IA-RUFISQUE": 92.5, "SN-IA-FATICK": 90.75,
    "SN-IA-KOLDA": 86.38, "SN-IA-KAOLACK": 74.63, "SN-IA-TAMBACOUNDA": 72.49,
    "SN-IA-LOUGA": 72.23, "SN-IA-MATAM": 67.51, "SN-IA-DIOURBEL": 58.20, "SN-IA-KAFFRINE": 46.94,
}

SOCLE = Socle([
    # dwibrlf (chômage)
    *[obs("dwibrlf", z, "2025", v, sexe="TOTAL", âge="TOTAL") for z, v in CHOMAGE_2025.items()],
    obs("dwibrlf", "SN", "2015", 14.5, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN", "2018", 16.0, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN", "2020", 17.5, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN", "2024", 19.5, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN", "2025", 20.4, sexe="TOTAL", âge="TOTAL"),
    # pvswjnd (population 2023)
    obs("pvswjnd", "SN-DK", "2023", 4004426, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-TH", "2023", 2463677, sexe="Total", age="Total"),
    obs("pvswjnd", "SN", "2023", 18126390, sexe="Total", age="Total"),
    # jcvcajc.taux-de-pauvrete
    *[obs("jcvcajc.taux-de-pauvrete", z, "2022", v, indicateurs="Taux de pauvreté",
          catégorie="Indices de pauvreté", **{"situation-matrimoniale-du-cm": "Ensemble",
          "taille-du-ménage": "Ensemble", "milieu-de-résidence": "Ensemble"})
      for z, v in PAUVRETE_2022.items()],
    obs("jcvcajc.taux-de-pauvrete", "SN", "2011", 46.7, indicateurs="Taux de pauvreté",
        catégorie="Indices de pauvreté", **{"situation-matrimoniale-du-cm": "Ensemble",
        "taille-du-ménage": "Ensemble", "milieu-de-résidence": "Ensemble"}),
    obs("jcvcajc.taux-de-pauvrete", "SN", "2022", 37.5, indicateurs="Taux de pauvreté",
        catégorie="Indices de pauvreté", **{"situation-matrimoniale-du-cm": "Ensemble",
        "taille-du-ménage": "Ensemble", "milieu-de-résidence": "Ensemble"}),
    # ervtjfc.taux-brut-de-scolarisation (16 académies)
    *[obs("ervtjfc.taux-brut-de-scolarisation", z, "2025", v, cycle="Elémentaire", sexe="Totale",
          indicateurs="Taux brut de scolarisation")
      for z, v in TBS_2025.items()],
    # feujxob.riz-brise-ordinaire-au-detail (Dakar, prix au détail)
    obs("feujxob.riz-brise-ordinaire-au-detail", "SN-DK", "2025-03", 399.88,
        indicateur="Riz brisé ordinaire au détail"),
    obs("feujxob.riz-brise-ordinaire-au-detail", "SN-DK", "2026-03", 309.03,
        indicateur="Riz brisé ordinaire au détail"),
], SOURCES)


# ===========================================================================
# 1. Classement (#14, EF-07, US-04)
# ===========================================================================

def test_classement_decroissant_14_regions_chomage():
    """FR-041 : Quelle région a le taux de chômage le plus élevé en 2025 ?
    Ordre décroissant, 1er attendu = Matam (48,0 %), tête en évidence."""
    req = RequeteStructuree(
        intention="classement",
        indicateur="dwibrlf",
        periode=Periode(type="annee", valeur="2025"),
        ordre="desc",
        confiance=0.9,
    )
    res = resoudre(SOCLE, req, question="Quelle région a le taux de chômage le plus élevé en 2025 ?")
    assert isinstance(res, Resolution)
    assert len(res.resultats) == 14

    # Ordre décroissant
    assert res.resultats[0].zone.code == "SN-MT"
    assert res.resultats[0].valeur == 48.0
    assert res.resultats[1].zone.code == "SN-KL"
    assert res.resultats[-1].zone.code == "SN-TC"
    assert res.resultats[-1].valeur == 5.0

    # Choix 2 : Mise en évidence de la tête de classement (pas de zone citée)
    assert res.resultats[0].mise_en_evidence is True
    assert all(not r.mise_en_evidence for r in res.resultats[1:])

    # Graphique en barres horizontales
    g = res.graphique
    assert g is not None
    assert g.type == "barres_horizontales"
    assert g.svg_url is None  # Décision 0016
    assert len(g.series) == 1
    assert len(g.series[0].points) == 14  # tous les points envoyés
    assert g.series[0].points[0].x == "Matam"
    assert g.series[0].points[0].mise_en_evidence is True
    assert g.series[0].points[1].mise_en_evidence is False
    assert g.pied.startswith("Source : ANSD") and g.pied.endswith("· gestukaay")

    # Choix 4 : Forme du gabarit d'explication
    exp = explication(res.resultats, intention="classement", ordre="desc")
    assert exp == "En 2025, la valeur la plus élevée est celle de Matam (48\u202f%), devant celles de Kaolack (37,2\u202f%) et de Sédhiou (30,2\u202f%)."


def test_classement_croissant_pauvrete():
    """FR-043 : Quelle région a le taux de pauvreté le plus bas ?
    Ordre croissant, 1er attendu = Dakar (9,3 %)."""
    req = RequeteStructuree(
        intention="classement",
        indicateur="jcvcajc.taux-de-pauvrete",
        periode=Periode(type="annee", valeur="2022"),
        ordre="asc",
        confiance=0.9,
    )
    res = resoudre(SOCLE, req, question="Quelle région a le taux de pauvreté le plus bas ?")
    assert isinstance(res, Resolution)
    assert len(res.resultats) == 14
    assert res.resultats[0].zone.code == "SN-DK"
    assert res.resultats[0].valeur == 9.3
    assert res.resultats[0].mise_en_evidence is True
    assert res.resultats[-1].zone.code == "SN-KE"
    assert res.resultats[-1].valeur == 65.7

    exp = explication(res.resultats, intention="classement", ordre="asc")
    assert exp == "En 2022, la valeur la plus faible est celle de Dakar (9,3\u202f%), devant celles de Thiès (29,9\u202f%) et de Saint-Louis (37,3\u202f%)."


def test_classement_education_16_academies():
    """FR-040 : Quelle région a le taux de scolarisation le plus élevé ?
    Éducation = 16 académies (choix 2), 1er attendu = SN-IA-ZIGUINCHOR."""
    req = RequeteStructuree(
        intention="classement",
        indicateur="ervtjfc.taux-brut-de-scolarisation",
        periode=Periode(type="annee", valeur="2025"),
        ordre="desc",
        confiance=0.9,
    )
    res = resoudre(SOCLE, req, question="Quelle région a le taux de scolarisation le plus élevé ?")
    assert isinstance(res, Resolution)
    assert len(res.resultats) == 16  # Exactement 16 académies
    assert res.resultats[0].zone.code == "SN-IA-ZIGUINCHOR"
    assert res.resultats[0].mise_en_evidence is True

    # Graphique titre par académie
    g = res.graphique
    assert g is not None
    assert "par académie" in g.titre
    assert len(g.series[0].points) == 16

    # Explication mentionne l'académie
    exp = explication(res.resultats, intention="classement", ordre="desc")
    assert "l'académie de Ziguinchor" in exp
    assert exp.startswith("En 2025, la valeur la plus élevée est celle de l'académie de Ziguinchor")


def test_classement_zone_citee_mise_en_evidence():
    """Si la question cite une zone (ex. Thiès), c'est elle qui est mise en évidence."""
    req = RequeteStructuree(
        intention="classement",
        indicateur="dwibrlf",
        zones=["SN-TH"],
        periode=Periode(type="annee", valeur="2025"),
        ordre="desc",
        confiance=0.9,
    )
    res = resoudre(SOCLE, req, question="Quel est le rang de Thiès pour le chômage en 2025 ?")
    assert isinstance(res, Resolution)
    assert len(res.resultats) == 14
    # Thiès est 8e dans le classement mais reçoit la mise en évidence
    thies = next(r for r in res.resultats if r.zone.code == "SN-TH")
    assert thies.mise_en_evidence is True
    # Matam (tête) n'a pas la mise en évidence car Thiès était citée
    assert res.resultats[0].mise_en_evidence is False

    g = res.graphique
    p_thies = next(p for p in g.series[0].points if p.x == "Thiès")
    assert p_thies.mise_en_evidence is True


# ===========================================================================
# 2. Comparaison spatiale et temporelle (#14, EF-07, US-04)
# ===========================================================================

def test_comparaison_spatiale_dakar_thies():
    """FR-029 : Population de Dakar et de Thiès en 2023.
    Deux zones, barres horizontales, les 2 zones en évidence."""
    req = RequeteStructuree(
        intention="comparaison",
        indicateur="pvswjnd",
        zones=["SN-DK", "SN-TH"],
        periode=Periode(type="annee", valeur="2023"),
        confiance=0.9,
    )
    res = resoudre(SOCLE, req, question="Population de Dakar et de Thiès en 2023")
    assert isinstance(res, Resolution)
    assert len(res.resultats) == 2
    assert all(r.mise_en_evidence for r in res.resultats)

    g = res.graphique
    assert g is not None
    assert g.type == "barres_horizontales"
    assert len(g.series[0].points) == 2
    assert all(p.mise_en_evidence for p in g.series[0].points)

    ind = indicateurs()["pvswjnd"]
    exp = comparaison(res.resultats, ind)
    assert "Dakar" in exp and "Thiès" in exp


def test_comparaison_temporelle_evolution_chomage():
    """FR-039 : Le chômage a-t-il augmenté au Sénégal entre 2015 et 2025 ?
    resultats = les 2 bornes demandées ;
    graphique = toutes les années publiées entre les deux, bornes en évidence ;
    explication = sens (hausse), aucun écart calculé."""
    req = RequeteStructuree(
        intention="comparaison",
        indicateur="dwibrlf",
        zones=["SN"],
        periode=Periode(type="annee", valeur="2015", fin="2025"),
        confiance=0.9,
    )
    res = resoudre(SOCLE, req, question="Le chômage a-t-il augmenté au Sénégal entre 2015 et 2025 ?")
    assert isinstance(res, Resolution)

    # resultats = seulement les périodes demandées
    assert len(res.resultats) == 2
    assert [r.periode.valeur for r in res.resultats] == ["2015", "2025"]
    assert res.resultats[0].valeur == 14.5
    assert res.resultats[1].valeur == 20.4
    assert all(r.mise_en_evidence for r in res.resultats)

    # graphique = courbe avec toutes les années publiées entre 2015 et 2025 (2015, 2018, 2020, 2024, 2025)
    g = res.graphique
    assert g is not None
    assert g.type == "courbe"
    assert g.svg_url is None
    points = g.series[0].points
    assert len(points) == 5
    assert [p.x for p in points] == ["2015", "2018", "2020", "2024", "2025"]
    # Bornes en évidence, intermédiaires sans
    assert points[0].mise_en_evidence is True   # 2015
    assert points[1].mise_en_evidence is False  # 2018
    assert points[2].mise_en_evidence is False  # 2020
    assert points[3].mise_en_evidence is False  # 2024
    assert points[4].mise_en_evidence is True   # 2025

    # Explication : seulement le sens de l'évolution (hausse / baisse), jamais l'écart calculé
    ind = indicateurs()["dwibrlf"]
    exp = comparaison(res.resultats, ind)
    assert "soit une évolution en hausse" in exp
    assert "14,5" in exp and "20,4" in exp
    assert "+" not in exp and "-" not in exp and "points" not in exp


def test_comparaison_temporelle_baisse_pauvrete():
    """FR-032 : Le taux de pauvreté a-t-il baissé entre 2011 et 2022 au Sénégal ?
    Baisse constatée, 2 bornes demandées."""
    req = RequeteStructuree(
        intention="comparaison",
        indicateur="jcvcajc.taux-de-pauvrete",
        zones=["SN"],
        periode=Periode(type="annee", valeur="2011", fin="2022"),
        confiance=0.9,
    )
    res = resoudre(SOCLE, req, question="Le taux de pauvreté a-t-il baissé entre 2011 et 2022 au Sénégal ?")
    assert isinstance(res, Resolution)
    assert len(res.resultats) == 2
    assert res.resultats[0].valeur == 46.7
    assert res.resultats[1].valeur == 37.5

    ind = indicateurs()["jcvcajc.taux-de-pauvrete"]
    exp = comparaison(res.resultats, ind)
    assert "soit une évolution en baisse" in exp


def test_comparaison_temporelle_repli_periodes_question():
    """Si requete.periode.fin n'est pas renseignée (repli sans v1.2.0),
    la résolution extrait les 2 périodes depuis la question."""
    req = RequeteStructuree(
        intention="comparaison",
        indicateur="dwibrlf",
        zones=["SN"],
        periode=Periode(type="annee", valeur="2015"),  # pas de fin
        confiance=0.9,
    )
    res = resoudre(SOCLE, req, question="Le chômage a-t-il augmenté au Sénégal entre 2015 et 2025 ?")
    assert isinstance(res, Resolution)
    assert len(res.resultats) == 2
    assert [r.periode.valeur for r in res.resultats] == ["2015", "2025"]


# ===========================================================================
# 3. Compréhension : règles locales (#14)
# ===========================================================================

def test_regles_comprehension_classement():
    """Vérifier que les questions de classement sont reconnues avec le bon ordre."""
    c1 = index().chercher("taux de chômage")
    r1 = regles("Quelle région a le taux de chômage le plus élevé en 2025 ?", c1, [], ["2025"], None)
    assert r1.intention == "classement"
    assert r1.ordre == "desc"

    # Croissant (« le plus bas », « le moins »)
    c2 = index().chercher("taux de pauvreté")
    r2 = regles("Quelle région a le taux de pauvreté le plus bas ?", c2, [], [], None)
    assert r2.intention == "classement"
    assert r2.ordre == "asc"

    c3 = index().chercher("électricité")
    r3 = regles("Quelle région a le moins accès à l'électricité ?", c3, [], [], None)
    assert r3.intention == "classement"
    assert r3.ordre == "asc"


def test_regles_comprehension_comparaison_temporelle():
    """Vérifier que les comparaisons temporelles capturent les deux périodes."""
    c = index().chercher("taux de pauvreté")
    r = regles("Le taux de pauvreté a-t-il baissé entre 2011 et 2022 au Sénégal ?", c, ["SN"], ["2011", "2022"], None)
    assert r.intention == "comparaison"
    assert r.periode.valeur == "2011"
    assert r.periode.fin == "2022"
