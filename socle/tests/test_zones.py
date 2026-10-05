import pytest
from gestukaay_socle.zones import niveau_de_colonne, resoudre, zones


def test_referentiel_complet_et_coherent():
    z = zones()
    assert sum(x.niveau == "pays" for x in z.values()) == 1
    assert sum(x.niveau == "region" for x in z.values()) == 14
    assert sum(x.niveau == "departement" for x in z.values()) == 46
    assert sum(x.niveau == "academie" for x in z.values()) == 16
    for x in z.values():
        if x.niveau == "region":
            assert x.parent == "SN"
        if x.niveau == "departement":
            assert z[x.parent].niveau == "region", x.code
            assert x.code.startswith(x.parent + "-"), x.code
        if x.niveau == "academie":
            assert z[x.parent].niveau == "region", x.code
            assert x.couvre and all(c in z for c in x.couvre), x.code
            assert all(z[c].niveau in ("region", "departement") for c in x.couvre), x.code
        else:
            assert not x.couvre and x.statut_wo in ("a_valider", "valide"), x.code  # 0009


def test_academies_de_dakar_ne_sont_pas_la_region():
    z = zones()
    assert z["SN-IA-DAKAR"].couvre == ("SN-DK-DAKAR",)
    assert z["SN-IA-PIKINE-GUEDIAWAYE"].couvre == (
        "SN-DK-PIKINE", "SN-DK-GUEDIAWAYE", "SN-DK-KEUR-MASSAR")
    assert z["SN-IA-KOLDA"].couvre == ("SN-KD",)


@pytest.mark.parametrize(
    "libelle,niveau,attendu",
    [
        # régions, toutes graphies
        ("Thiès", None, "SN-TH"),
        ("THIES", None, "SN-TH"),
        ("Tiés", None, "SN-TH"),
        ("Cees", None, "SN-TH"),
        ("Kees", None, "SN-TH"),
        ("Saint Louis", None, "SN-SL"),
        ("Ndar", None, "SN-SL"),
        ("Région de Kolda", None, "SN-KD"),
        ("Sénégal", None, "SN"),
        # départements sans homonyme
        ("Mbour", None, "SN-TH-MBOUR"),
        ("M’Bour", None, "SN-TH-MBOUR"),
        ("M'bour", None, "SN-TH-MBOUR"),
        ("Dpt M'bour", None, "SN-TH-MBOUR"),
        ("Velingara", None, "SN-KD-VELINGARA"),
        ("Malem Hoddar", None, "SN-KA-MALEM-HODAR"),
        # homonymes : région par défaut, département si le contexte le dit
        ("Kaolack", None, "SN-KL"),
        ("Kaolack", "departement", "SN-KL-KAOLACK"),
        ("Dpt Thiès", None, "SN-TH-THIES"),
        ("Dakar Department", None, "SN-DK-DAKAR"),
        ("Département de Ziguinchor", None, "SN-ZG-ZIGUINCHOR"),
        # le marqueur l'emporte sur le niveau demandé
        ("Région de Kaolack", "departement", "SN-KL"),
        # académies : seulement si le contexte le dit, jamais par défaut
        ("IA Kolda", None, "SN-IA-KOLDA"),
        ("IA Pikine-Guédiawaye", None, "SN-IA-PIKINE-GUEDIAWAYE"),
        ("Kolda", "academie", "SN-IA-KOLDA"),
        ("Pikine", "academie", "SN-IA-PIKINE-GUEDIAWAYE"),
        ("Dakar", "academie", "SN-IA-DAKAR"),
        ("National", "academie", "SN"),
        ("Pikine", None, "SN-DK-PIKINE"),
        ("Dakar", None, "SN-DK"),
        # jamais rattachés
        ("Total", None, None),
        ("ALL", None, None),
        ("Urbain", None, None),
        ("Zone OUEST", None, None),
        ("Paris", None, None),
        ("", None, None),
    ],
)
def test_resoudre(libelle, niveau, attendu):
    assert resoudre(libelle, niveau) == attendu


@pytest.mark.parametrize(
    "colonne,attendu",
    [("inspection-académique", "academie"), ("academie", "academie"), ("département", "departement"),
     ("régions-et-départements", None), ("region", None)],
)
def test_niveau_de_colonne(colonne, attendu):
    assert niveau_de_colonne(colonne) == attendu
