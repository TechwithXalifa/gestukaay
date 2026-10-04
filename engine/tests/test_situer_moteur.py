"""« Où je me situe » (#95, décisions 0004 §2, 0012, 0022). Socle synthétique : tourne en CI, sans réseau.

Valeurs vérifiées dans le socle 2026.10.0 (et dans contracts/examples/situer.json, 0012), sauf celles
marquées « fictive », qui ne servent qu'à vérifier qu'on ne les prend pas.
"""

from datetime import date

import pytest
from gestukaay_contracts.models import SituateRequest, SituateResponse
from gestukaay_engine import SaisieInvalide
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.fake import EXEMPLES
from gestukaay_engine.moteur import MoteurReel
from gestukaay_engine.situer import intervalle, situer
from gestukaay_engine.socle import Observation, Socle, SourceJeu


def obs(ind, zone, periode, valeur, **dims):
    return Observation(id=f"{ind}-{zone}-{periode}-{valeur}-{len(dims)}", indicateur=ind, zone=zone,
                       zone_presumee=False, periode=periode, desagregation=tuple(sorted(dims.items())),
                       valeur=valeur, unite="", echelle="1", source_id=ind.split(".")[0], nature="observee",
                       base_projection="")


def conso(zone, periode, valeur, milieu="Ensemble"):
    return obs("jcvcajc.total", zone, periode, valeur, **{
        "catégorie": "Consommation moyenne par tête", "milieu-de-résidence": milieu,
        "situation-matrimoniale-du-cm": "Ensemble", "taille-du-ménage": "Ensemble"})


def pauvrete(taille, valeur):
    return obs("jcvcajc.taux-de-pauvrete", "SN", "2022", valeur, **{
        "catégorie": "Indices de pauvreté", "milieu-de-résidence": "Ensemble",
        "situation-matrimoniale-du-cm": "Ensemble", "taille-du-ménage": taille})


SOURCES = {d: SourceJeu(d, "ANSD", "Agence nationale", f"Jeu {d}", date(2024, 7, 15), "", f"https://x/{d}")
           for d in ("jcvcajc", "qjyrtof", "asongtc")}
SOCLE = Socle([
    conso("SN-KD", "2022", 387934), conso("SN", "2022", 542706), conso("SN-DK", "2022", 861364),
    conso("SN-KD", "2019", 300000),               # fictive : une période plus ancienne
    conso("SN-KD", "2022", 999999, "Urbain"),     # fictive : on compare à « Ensemble »
    *[pauvrete(t, v) for t, v in (("1-4 personnes", 4.6), ("5-9 personnes", 24.2), ("10-14 personnes", 41.8),
                                  ("15-19 personnes", 59.3), ("22 personnes ou plus", 66.4), ("Ensemble", 37.5))],
    obs("qjyrtof.le-plus-bas", "SN-KD", "2023", 63.0,
        **{"catégorie": "Quintile de bien-être économique", "milieu-de-résidence": "Ensemble"}),
    obs("asongtc", "SN-KD", "2023", 39.6, **{"milieu-de-résidence": "Total"}),
], SOURCES, "test")


def demander(region, taille, tranche):
    return situer(SOCLE, SituateRequest(region=region, taille_menage=taille, depenses_mensuelles=tranche))


def test_exemple_du_contrat_reproduit():
    ex = SituateResponse.model_validate_json((EXEMPLES / "situer.json").read_text(encoding="utf-8"))
    r = demander("SN-KD", 7, "100k_200k")
    assert r.depense_par_personne_an == ex.depense_par_personne_an
    assert (r.position_region, r.position_pays) == (ex.position_region, ex.position_pays)
    assert (r.moyenne_region.valeur, r.moyenne_pays.valeur) == (387934, 542706)
    assert r.explication == ex.explication
    assert [(c.indicateur.libelle, c.zone.code, c.valeur) for c in r.contexte] == \
        [(c.indicateur.libelle, c.zone.code, c.valeur) for c in ex.contexte]


def test_tranche_ouverte_au_dessus_si_la_borne_basse_depasse_la_moyenne():
    """0012 : Dakar, 7 personnes, plus de 1 000 000 par mois -> au-dessus."""
    r = demander("SN-DK", 7, "plus_1m")
    assert (r.position_region, r.depense_par_personne_an.maximum) == ("au_dessus", None)


def test_tranche_ouverte_sinon_autour_avec_au_moins():
    """0012 : Dakar, 25 personnes -> autour, et « au moins X FCFA par personne »."""
    r = demander("SN-DK", 25, "plus_1m")
    assert r.position_region == "autour"
    assert r.explication.startswith("Votre ménage dépense au moins 480 000 FCFA par personne et par an.")


def test_plus_500k_depreciee_meme_regle():
    r = demander("SN-DK", 10, "plus_500k")  # au moins 600 000 : sous Dakar, au-dessus du Sénégal
    assert (r.position_region, r.position_pays) == ("autour", "au_dessus")


def test_tranche_la_plus_basse():
    iv = intervalle("moins_50k", 4)
    assert (iv.minimum, iv.maximum, iv.libelle) == (0, 150000, "moins de 150 000 FCFA par personne et par an")


@pytest.mark.parametrize("taille, attendu", [(1, "1 à 4"), (9, "5 à 9"), (19, "15 à 19"), (22, "22 personnes ou plus"),
                                             (40, "22 personnes ou plus")])
def test_pauvrete_des_menages_de_meme_taille(taille, attendu):
    assert attendu in demander("SN-KD", taille, "100k_200k").contexte[0].indicateur.libelle


@pytest.mark.parametrize("taille", [20, 21])
def test_aucune_tranche_publiee_pour_20_ou_21_personnes(taille):
    libelles = [c.indicateur.libelle for c in demander("SN-KD", taille, "100k_200k").contexte]
    assert not any("pauvreté" in x for x in libelles) and len(libelles) == 2


@pytest.mark.parametrize("region", ["SN-KD-KOLDA", "SN", "SN-XX"])
def test_region_invalide(region):
    with pytest.raises(SaisieInvalide):
        demander(region, 5, "100k_200k")


def test_moteur_reel_situe():
    r = MoteurReel(SOCLE, Comprehension(None)).situer(
        SituateRequest(region="SN-KD", taille_menage=7, depenses_mensuelles="100k_200k"))
    assert r.position_region == "en_dessous" and r.version_contrat
