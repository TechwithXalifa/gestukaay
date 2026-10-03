"""Extraction vers le schéma 10.3 (#4). Lignes synthétiques : tourne en CI, sans le socle brut."""

import itertools
import json
from dataclasses import fields

from gestukaay_socle.extraction import (
    colonnes_geo,
    extraire,
    index_indicateurs,
    observation_id,
    periode,
    zone_de_ligne,
    zones_par_jeu,
)
from gestukaay_socle.indicateurs import Indicateur

REGIONS = ["Dakar", "Diourbel", "Fatick", "Kaffrine", "Kaolack", "Kédougou", "Kolda", "Louga", "Matam",
           "Saint-Louis", "Sédhiou", "Tambacounda", "Thiès", "Ziguinchor"]


def ligne(ds, valeur, dims, periode_="2023-01-01T00:00:00Z", freq="A", unite="%", region_id=""):
    return {"dataset_id": ds, "valeur": valeur, "desagregation_json": json.dumps(dims, ensure_ascii=False),
            "periode": periode_, "frequence": freq, "unite": unite, "echelle": "1", "region_id": region_id}


def indicateur(code, ds, valeur_portail="", unite="%", verification="a_verifier"):
    """Indicateur minimal ; les autres colonnes du référentiel restent vides (robuste aux ajouts)."""
    base = {f.name: "" for f in fields(Indicateur)} | {"questions_test": (), "niveaux_zone": (),
                                                        "desagregations": (), "nb_valeurs": 1}
    return Indicateur(**base | {
        "code": code, "dataset_id": ds, "libelle_fr": code, "unite": unite, "domaine": "D", "priorite": "P3",
        "verification": verification, "dimension_indicateur": "indicateurs" if valeur_portail else "",
        "valeur_portail": valeur_portail, "jeu": ds})


def test_periode():
    assert periode("2023-01-01T00:00:00Z", "A") == "2023"
    assert periode("2026-03-01T00:00:00Z", "M") == "2026-03"
    assert periode("2023-04-01T00:00:00Z", "Q") == "2023-T2"
    assert periode("2024-05-17T00:00:00Z", "D") == "2024-05-17"


def test_observation_id_stable():
    a = observation_id("x", "2023", {"sexe": "Total", "régions": "Dakar"}, "%")
    assert a == observation_id("x", "2023", {"régions": "Dakar", "sexe": "Total"}, "%")
    assert a != observation_id("x", "2023", {"régions": "Dakar", "sexe": "Total"}, "Nombre")
    assert len(a) == 16


def test_colonne_geographique_jeu_par_jeu():
    lignes = [ligne("a", "1", {"regions": r}) for r in REGIONS]
    lignes += [ligne("b", "1", {"regions": r}) for r in ("Dakar", "Thiès", "Kolda")]
    lignes += [ligne("c", "1", {"regions": "Dakar"})]  # une seule zone : pas une colonne géographique
    geo = colonnes_geo(lignes)
    assert geo == {"a": {"regions": True}, "b": {"regions": False}}


def test_zone_de_ligne():
    national, regional = {"regions": True}, {"regions": False}
    assert zone_de_ligne({"regions": "Thiès"}, national, "", None) == ("SN-TH", False, "")
    # Total : Sénégal seulement si la colonne couvre les 14 régions
    assert zone_de_ligne({"regions": "Total"}, national, "", None) == ("SN", False, "")
    assert zone_de_ligne({"regions": "Total"}, regional, "", None)[0] is None
    # la zone la plus fine l'emporte ; un total à côté est ignoré
    geo2 = {"region": True, "departement": False}
    assert zone_de_ligne({"region": "Thiès", "departement": "Mbour"}, geo2, "", None)[0] == "SN-TH-MBOUR"
    assert zone_de_ligne({"region": "Thiès", "departement": "Total"}, geo2, "", None)[0] == "SN-TH"
    # plus fin que le référentiel : rejeté, avec le motif
    z, _, motif = zone_de_ligne({"regions": "ARD. KOUMBAL"}, national, "", None)
    assert z is None and motif.startswith("infra")
    # jeu sans colonne géographique : exception, puis code du portail, puis Sénégal présumé
    assert zone_de_ligne({}, {}, "", "SN-DK") == ("SN-DK", False, "")
    assert zone_de_ligne({}, {}, "SN-KL", None) == ("SN-KL", False, "")
    assert zone_de_ligne({}, {}, "", None) == ("SN", True, "")


def test_prix_feujxob_a_dakar():
    assert zones_par_jeu()["feujxob"] == "SN-DK"


def test_extraire():
    ind = {
        "x.taux": indicateur("x.taux", "x", "Taux"),
        "y": indicateur("y", "y", unite="Nombre"),
        "z": indicateur("z", "z", unite="Nombre", verification="ecarte"),
    }
    brutes = [
        ligne("x", "10.5", {"indicateurs": "Taux", "regions": "Thiès", "sexe": "Total"}),
        ligne("x", "10.5", {"indicateurs": "taux", "regions": "Thiès", "sexe": "Total"}),  # graphie, même valeur
        ligne("x", "", {"indicateurs": "Taux", "regions": "Kolda", "sexe": "Total"}),  # vide : ignorée
        ligne("x", "3", {"indicateurs": "Inconnu", "regions": "Thiès"}),
        ligne("y", "7", {}, unite="Nombre"),
        ligne("y", "8", {}, unite="Nombre", periode_="2024-01-01T00:00:00Z"),
        ligne("y", "9", {}, unite="Nombre", periode_="2024-06-01T00:00:00Z"),  # même année, autre valeur
        ligne("z", "1", {}, unite="Nombre"),
    ]
    geo = {"x": {"regions": False}}
    res = extraire(enumerate(brutes, 2), geo, index_indicateurs(ind), {})
    obs = {(o[1], o[2], o[4]): o for o in res.observations}
    assert set(obs) == {("x.taux", "SN-TH", "2023"), ("y", "SN", "2023")}
    o = obs[("x.taux", "SN-TH", "2023")]
    assert json.loads(o[5]) == {"sexe": "Total"}  # ni la zone ni l'indicateur dans la désagrégation
    assert o[6] == "10.5" and o[12] == 2  # valeur telle que publiée, ligne d'origine
    assert o[10] == "observee"
    assert obs[("y", "SN", "2023")][3] == "oui"  # zone présumée
    assert res.stats["doublons identiques fusionnés"] == 1
    motifs = sorted(r[3] for r in res.rejets)
    assert motifs == ["doublon conflictuel", "doublon conflictuel", "indicateur absent du référentiel",
                      "indicateur écarté"]


def test_nature_par_periode():
    from gestukaay_socle.extraction import RegleNature, nature_de
    rnumqzf = [RegleNature("2016", "2022", "estimation", "Rétropolation"),
               RegleNature("2023", "2023", "observee", ""),
               RegleNature("2024", "2025", "projection", "Projections démographiques 2023-2073")]
    assert nature_de("2020", rnumqzf, "2026") == ("estimation", "Rétropolation")
    assert nature_de("2023", rnumqzf, "2026") == ("observee", "")
    assert nature_de("2025", rnumqzf, "2026") == ("projection", "Projections démographiques 2023-2073")
    # une année postérieure à la dernière mise à jour ne peut pas être observée
    assert nature_de("2035", [], "2022") == ("projection", "")
    assert nature_de("2026-03", [], "2026") == ("observee", "")


def test_referentiel_des_natures():
    import csv as _csv

    from gestukaay_socle.extraction import FICHIER_NATURES, NATURES, natures
    with FICHIER_NATURES.open(encoding="utf-8") as f:
        lignes = list(_csv.DictReader(f, delimiter=";"))
    for r in lignes:
        assert r["nature"] in NATURES and r["preuve"], r
        assert (r["nature"] == "projection") <= bool(r["base_projection"]), r  # toute projection a sa base
        assert not (r["periode_debut"] and r["periode_fin"]) or r["periode_debut"] <= r["periode_fin"], r
    # périodes d'un même jeu sans chevauchement
    for ds, regles in natures().items():
        bornes = sorted((r.debut or "0000", r.fin or "9999") for r in regles)
        assert all(a[1] < b[0] for a, b in itertools.pairwise(bornes)), ds
    assert natures()["pexioke"][0].nature == "projection"  # espérance de vie : série RGPHAE 2013
