"""Espace Données du moteur réel : catalogue, fiche et séries (décision 0023, #156). Socle synthétique :
tourne en CI, sans réseau. Les valeurs reprennent les exemples du contrat (series.json,
fiche_indicateur.json), eux-mêmes tirés du socle 2026.10.0 ; celles marquées « fictive » ne servent qu'à
vérifier qu'on ne les prend pas.
"""

import json
from datetime import date

import pytest
from gestukaay_contracts.models import FicheIndicateur
from gestukaay_engine import IndicateurInconnu
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.donnees import catalogue, fiche, series
from gestukaay_engine.fake import EXEMPLES
from gestukaay_engine.moteur import MoteurReel
from gestukaay_engine.socle import Observation, Socle, SourceJeu

PAUVRETE = "jcvcajc.taux-de-pauvrete"
CONSO = "jcvcajc.total"
POPULATION = "pvswjnd"  # RGPH-5, une seule période


def obs(ind, zone, periode, valeur, oid=None, **dims):
    return Observation(id=oid or f"{ind}-{zone}-{periode}-{valeur}", indicateur=ind, zone=zone, zone_presumee=False,
                       periode=periode, desagregation=tuple(sorted(dims.items())), valeur=valeur, unite="%",
                       echelle="1", source_id=ind.split(".")[0], nature="observee", base_projection="")


def pauvrete(zone, periode, valeur, oid=None, milieu="Ensemble"):
    return obs(PAUVRETE, zone, periode, valeur, oid, **{
        "catégorie": "Indices de pauvreté", "milieu-de-résidence": milieu,
        "situation-matrimoniale-du-cm": "Ensemble", "taille-du-ménage": "Ensemble"})


SERIES = json.loads((EXEMPLES / "series.json").read_text(encoding="utf-8"))
SOURCES = {
    "jcvcajc": SourceJeu("jcvcajc", "ANSD", "Agence nationale", "10.1_Indices de pauvreté", date(2024, 7, 15), "",
                         "https://senegal.opendataforafrica.org/jcvcajc"),
    "pvswjnd": SourceJeu("pvswjnd", "ANSD", "Agence nationale", "RGPH-5", date(2023, 10, 31), "", "https://x/pvswjnd"),
}
SOCLE = Socle([
    *[pauvrete(s["zone"]["code"], p["periode"], p["valeur"], p["observation_id"]) for s in SERIES["series"] for p in s["points"]],
    pauvrete("SN-DK", "2022", 99.9, milieu="Urbain"),  # fictive : Explorer sert le total (« Ensemble »)
    obs(CONSO, "SN", "2022", 542706, **{"catégorie": "Consommation moyenne par tête", "milieu-de-résidence": "Ensemble",
                                        "situation-matrimoniale-du-cm": "Ensemble", "taille-du-ménage": "Ensemble"}),
    obs(POPULATION, "SN", "2023", 18126390), obs(POPULATION, "SN-TH", "2023", 2463677),
], SOURCES, "test")


# --------------------------------------------------------------------------------------------- catalogue

def test_catalogue_seulement_les_indicateurs_qui_ont_des_valeurs():
    c = catalogue(SOCLE)
    assert c.total == 3 and {i.code for i in c.indicateurs} == {PAUVRETE, CONSO, POPULATION}
    assert c.version_socle == "test"


def test_catalogue_verifies_d_abord_puis_par_libelle():
    verifies = [i.verifie for i in catalogue(SOCLE).indicateurs]
    assert verifies == sorted(verifies, reverse=True)


def test_catalogue_ligne_complete():
    p = next(i for i in catalogue(SOCLE).indicateurs if i.code == PAUVRETE)
    attendu = FicheIndicateur.model_validate_json((EXEMPLES / "fiche_indicateur.json").read_text(encoding="utf-8")).indicateur
    assert (p.libelle, p.domaine, p.unite, p.producteur, p.operation) == (
        attendu.libelle, attendu.domaine, attendu.unite, attendu.producteur, attendu.operation)
    assert p.niveaux == ["pays", "region"] and (p.periode_debut, p.periode_fin) == ("2011", "2022")


def test_catalogue_filtres_et_pages():
    assert [i.code for i in catalogue(SOCLE, q="taux de pauvreté").indicateurs] == [PAUVRETE]
    assert catalogue(SOCLE, q="PAUVRETE taux").total == 1  # accents, casse, mots dans n'importe quel ordre
    assert catalogue(SOCLE, q="pauvreté").total == 2  # le domaine compte aussi : la consommation par tête
    assert [i.code for i in catalogue(SOCLE, q="rgph").indicateurs] == [POPULATION]  # l'opération aussi
    assert catalogue(SOCLE, niveau="region").total == 2
    assert catalogue(SOCLE, niveau="academie").total == 0
    assert catalogue(SOCLE, domaine="pauvrete").total == catalogue(SOCLE, domaine="Pauvreté").total == 2
    page = catalogue(SOCLE, limite=1, decalage=1)
    assert page.total == 3 and len(page.indicateurs) == 1


# --------------------------------------------------------------------------------------------- fiche

def test_fiche_reproduit_l_exemple_du_contrat():
    ex = FicheIndicateur.model_validate_json((EXEMPLES / "fiche_indicateur.json").read_text(encoding="utf-8"))
    f = fiche(SOCLE, PAUVRETE, date(2026, 10, 4))
    assert f.definition == ex.definition  # citée du portail, jamais rédigée (0005)
    # mêmes niveaux et périodes ; le socle synthétique n'a que 2 régions sur les 14 publiées
    assert [(c.niveau, c.periodes) for c in f.couverture] == [(c.niveau, c.periodes) for c in ex.couverture]
    assert [c.zones for c in f.couverture] == [1, 2]
    assert f.source.libelle == ex.source.libelle and f.source.url == ex.source.url
    assert f.citation == ex.citation
    assert f.indicateurs_lies[0].code == CONSO and len(f.indicateurs_lies) <= 6


def test_fiche_code_inconnu_ou_sans_valeur():
    with pytest.raises(IndicateurInconnu):
        fiche(SOCLE, "inconnu.code")
    with pytest.raises(IndicateurInconnu):
        fiche(SOCLE, "jcvcajc.profondeur-de-la-pauvrete")  # au référentiel, mais aucune valeur dans ce socle


# --------------------------------------------------------------------------------------------- séries

def test_series_reproduit_l_exemple_du_contrat():
    s = series(SOCLE, PAUVRETE, ["SN", "SN-DK", "SN-KD"])
    obtenu = [(x.zone.code, [(p.periode, p.valeur_affichee, p.observation_id) for p in x.points]) for x in s.series]
    attendu = [(x["zone"]["code"], [(p["periode"], p["valeur_affichee"], p["observation_id"]) for p in x["points"]])
               for x in SERIES["series"]]
    assert obtenu == attendu  # Dakar 2022 = 9,3 (Ensemble), pas la valeur urbaine fictive
    assert s.unite == "%" and s.absents == [] and s.desagregation is None
    assert s.graphique.type == "courbe" and s.graphique.titre == SERIES["graphique"]["titre"]
    assert s.graphique.pied == SERIES["graphique"]["pied"]


def test_series_zone_sans_valeur_signalee_jamais_interpolee():
    s = series(SOCLE, PAUVRETE, ["SN", "SN-TH", "SN-ZZ"])
    assert [x.zone.code for x in s.series] == ["SN"] and s.absents == ["SN-TH", "SN-ZZ"]


def test_series_periode_bornee():
    s = series(SOCLE, PAUVRETE, ["SN-DK"], debut="2019", fin="2022")
    assert [p.periode for p in s.series[0].points] == ["2019", "2022"]
    assert series(SOCLE, PAUVRETE, ["SN"], debut="2030").absents == ["SN"]


def test_series_une_seule_periode_donne_des_barres_triees():
    s = series(SOCLE, POPULATION, ["SN-TH", "SN"])
    assert s.graphique.type == "barres_horizontales"
    assert [p.x for p in s.graphique.series[0].points] == ["Sénégal", "Thiès"]  # de la plus grande à la plus petite


def test_series_indicateur_inconnu():
    with pytest.raises(IndicateurInconnu):
        series(SOCLE, "inconnu.code", ["SN"])


# --------------------------------------------------------------------------------------------- moteur réel

def test_moteur_reel_ne_repond_plus_503():
    m = MoteurReel(socle_=SOCLE, comprehension=Comprehension(None))
    assert m.catalogue().total == 3
    assert m.fiche(PAUVRETE).indicateur.code == PAUVRETE
    assert m.series(PAUVRETE, ["SN"]).series[0].points[-1].valeur_affichee == "37,5"
