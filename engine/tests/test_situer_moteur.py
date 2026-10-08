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


# --- v1.6.0 (décision 0039) -------------------------------------------------------------------------------

def _seuil(valeur=333441):
    return obs("ahjjzgc.seuil-de-pauvrete", "SN", "2018", valeur,
               domaine="Cadre de vie et pauvreté selon le sexe du chef de ménage", sexe="Ensemble", sources="EHCVM")


def _groupe(zone, quintile, valeur, periode="2023"):
    return obs("sfxudug", zone, periode, valeur, **{"milieu-de-résidence": "Total", "quintile": quintile})


GROUPES_KD = [("Le plus bas", 63.0), ("Second", 18.7), ("Moyen", 8.7), ("Quatrième", 6.7), ("Le plus élevé", 2.9)]
SOURCES_V2 = {**SOURCES, **{d: SourceJeu(d, "ANSD", "Agence nationale", f"Jeu {d}", date(2024, 7, 15), "",
                                         f"https://x/{d}") for d in ("ahjjzgc", "sfxudug")}}
SOCLE_V2 = Socle([
    conso("SN-KD", "2022", 387934), conso("SN", "2022", 542706), conso("SN-DK", "2022", 861364),
    conso("SN-TH", "2019", 500000),  # fictive : une autre période, absente de la carte
    conso("SN", "2022", 402240, "Rural"), conso("SN", "2022", 697989, "Urbain"),
    _seuil(), *[_groupe("SN-KD", q, v) for q, v in GROUPES_KD],
    _groupe("SN-DK", "Le plus bas", 1.0),  # fictive : un seul groupe publié, pas de répartition
], SOURCES_V2, "test")


def _espaces(texte: str) -> str:
    return texte.replace("\u202f", " ").replace("\u00a0", " ")


def demander_v2(region="SN-KD", taille=7, tranche="100k_200k", milieu=None):
    return situer(SOCLE_V2, SituateRequest(region=region, taille_menage=taille, depenses_mensuelles=tranche,
                                           milieu=milieu))


def test_milieu_compare_aux_menages_ruraux_du_senegal():
    r = demander_v2(milieu="rural")
    assert r.moyenne_milieu.valeur == 402240 and r.position_milieu == "en_dessous"
    assert r.moyenne_milieu.indicateur.libelle == "Consommation moyenne par tête des ménages ruraux"
    assert "Par rapport aux ménages ruraux du Sénégal (402 240 FCFA), c'est moins que" in _espaces(r.explication)
    assert r.moyenne_region.valeur == 387934  # la région reste comparée à « Ensemble »


def test_sans_milieu_pas_de_comparaison_au_milieu():
    r = demander_v2()
    assert r.moyenne_milieu is None and r.position_milieu is None and "ménages ruraux" not in r.explication


def test_seuil_de_pauvrete():
    r = demander_v2()  # 171 429 à 342 857 FCFA par personne : le seuil (333 441) est dans l'intervalle
    assert r.seuil_pauvrete.valeur == 333441 and r.position_seuil == "autour"
    assert "seuil de pauvreté officiel est de 333 441 FCFA par personne et par an (enquête de 2018)" in \
        _espaces(r.explication)
    assert demander_v2(taille=1, tranche="plus_1m").position_seuil == "au_dessus"
    assert demander_v2(taille=10, tranche="moins_50k").position_seuil == "en_dessous"


def test_phrases_ajoutees_avant_les_precautions():
    e = demander_v2(milieu="urbain").explication
    assert e.index("ménages urbains") < e.index("Une moyenne additionne") < e.index("Deux précautions")


def test_repartition_des_cinq_groupes_sans_y_placer_le_menage():
    r = demander_v2()
    assert [g.valeur for g in r.repartition_bien_etre] == [63.0, 18.7, 8.7, 6.7, 2.9]
    assert r.repartition_bien_etre[0].indicateur.libelle == "Groupe de bien-être le plus bas"
    assert demander_v2(region="SN-DK").repartition_bien_etre == []  # un seul groupe publié : rien


def test_moyennes_des_regions_de_la_meme_periode():
    r = demander_v2()
    assert [(x.zone.code, x.valeur) for x in r.moyennes_regions] == [("SN-DK", 861364), ("SN-KD", 387934)]


def test_faux_moteur_v16():
    from gestukaay_engine.fake import MoteurFactice
    f = MoteurFactice()
    avec = f.situer(SituateRequest(region="SN-KD", taille_menage=7, depenses_mensuelles="100k_200k", milieu="rural"))
    sans = f.situer(SituateRequest(region="SN-KD", taille_menage=7, depenses_mensuelles="100k_200k"))
    assert avec.moyenne_milieu and sans.moyenne_milieu is None and sans.seuil_pauvrete and sans.moyennes_regions
    # revue de SAN : sans milieu, ni la valeur ni la phrase qui la cite (402 240 FCFA sans sa source)
    assert "ménages ruraux du Sénégal" in avec.explication and "ménages ruraux" not in sans.explication
    assert "Le seuil de pauvreté officiel" in sans.explication  # le reste de l'explication est gardé
