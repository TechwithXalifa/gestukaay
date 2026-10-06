"""Tests de la correspondance approchée (issue #12).

Socle synthétique : tourne en CI, sans le socle extrait.
"""

from datetime import date

from gestukaay_contracts.models import Periode, RequeteStructuree
from gestukaay_engine.approchee import (
    Approchee,
    modalite_citee,
    proposer_approchee,
    rattachements,
)
from gestukaay_engine.resolution import Introuvable, resoudre
from gestukaay_engine.socle import Observation, Socle, SourceJeu


def obs(ind, zone, periode, valeur, nature="observee", base="", **dims):
    return Observation(
        id=f"{ind}-{zone}-{periode}-{valeur}",
        indicateur=ind,
        zone=zone,
        zone_presumee=False,
        periode=periode,
        desagregation=tuple(sorted(dims.items())),
        valeur=valeur,
        unite="",
        echelle="1",
        source_id=ind.split(".")[0],
        nature=nature,
        base_projection=base,
    )


SOURCES = {
    d: SourceJeu(d, "ANSD", "ANSD", f"Jeu {d}", date(2023, 10, 31), "", "")
    for d in (
        "pvswjnd",
        "ervtjfc",
        "jcvcajc",
        "dwibrlf",
        "asongtc",
        "iocwzud",
        "qbvttzc",
    )
}

SOCLE = Socle(
    [
        obs("pvswjnd", "SN", "2023", 18126390, sexe="Total", age="Total"),
        obs("pvswjnd", "SN-TH", "2023", 2463677, sexe="Total", age="Total"),
        obs("pvswjnd", "SN-DB", "2023", 2080333, sexe="Total", age="Total"),
        obs("ervtjfc.taux-brut-de-scolarisation", "SN-IA-DAKAR", "2025", 90.0),
        obs("ervtjfc.taux-brut-de-scolarisation", "SN-IA-DAKAR", "2024", 88.0),
        obs("jcvcajc.taux-de-pauvrete", "SN", "2022", 37.5),
        obs("jcvcajc.taux-de-pauvrete", "SN", "2019", 42.0),
        obs("jcvcajc.taux-de-pauvrete", "SN", "2011", 46.7),
        obs("dwibrlf", "SN-KL", "2025", 37.2),
        obs("dwibrlf", "SN-KL", "2024", 35.0),
        obs("dwibrlf", "SN-KL", "2023", 33.0),
        obs("asongtc", "SN-DK", "2023", 98.2),
        obs("asongtc", "SN", "2023", 77.0),
        obs("iocwzud", "SN", "2022", 12.0),
        obs("iocwzud", "SN", "2021", 11.5),
        obs("qbvttzc", "SN-KD", "2021", 9317, catégories="TOTAL"),
        obs("qbvttzc", "SN-KD", "2021", 5000, catégories="VPP"),
        obs("qbvttzc", "SN-ZG", "2021", 16221, catégories="TOTAL"),
        obs("qbvttzc", "SN-ZG", "2021", 9000, catégories="VPP"),
    ],
    SOURCES,
)


def test_rattachements_declares_avec_preuve():
    rats = rattachements()
    assert "touba" in rats
    assert "ville de thies" in rats
    assert "voitures" in rats
    for r in rats.values():
        assert r.preuve, f"preuve manquante pour {r.terme}"
        assert r.type in ("lieu", "modalite")


def test_approchee_lieu_rattache_complete_par_le_niveau_au_dessus():
    # « ville de Thiès » sur pvswjnd (région seulement, 2023 seulement) : le département n'est pas
    # publié ; la région puis le Sénégal complètent les choix (#116, choix KBD, repli (a) de la 0015)
    req = RequeteStructuree(
        intention="valeur",
        indicateur="pvswjnd",
        zones=["SN-TH"],
        periode=Periode(type="annee", valeur="2023"),
        confiance=0.4,
    )
    intr = Introuvable("zone_non_couverte", "lieu hors référentiel : ville de Thiès")
    res = proposer_approchee(
        SOCLE, req, intr, "Population de la ville de Thiès en 2023", "fr", ["ville de Thiès"]
    )
    assert isinstance(res, Approchee)
    assert [ch.requete.zones for ch in res.choix] == [["SN-TH"], ["SN"]]
    assert "pour la ville de Thiès ;" in res.reformulation  # avec l'article
    # aucun chiffre hors années dans les choix (EF-06) : « RGPH-5 » écrit en toutes lettres
    assert res.choix[0].libelle.startswith("Population (recensement de 2023) - Région de Thiès")


def test_approchee_touba_region_puis_senegal():
    req = RequeteStructuree(intention="valeur", indicateur="pvswjnd", zones=[],
                            periode=Periode(type="derniere"), confiance=0.9)
    intr = Introuvable("zone_non_couverte", "lieu hors référentiel : Touba")
    res = proposer_approchee(SOCLE, req, intr, "Combien d'habitants à Touba ?", "fr", ["Touba"])
    assert isinstance(res, Approchee)
    assert [ch.requete.zones for ch in res.choix] == [["SN-DB"], ["SN"]]
    assert "pour Touba ;" in res.reformulation


def test_approchee_multi_academies_dakar():
    req = RequeteStructuree(
        intention="valeur",
        indicateur="ervtjfc.taux-brut-de-scolarisation",
        zones=["SN-DK"],
        periode=Periode(type="derniere"),
        confiance=1.0,
    )
    intr = Introuvable("zone_non_couverte", "SN-DK non publié")
    res = proposer_approchee(SOCLE, req, intr, "Quel est le taux de scolarisation à Dakar ?", "fr")
    assert isinstance(res, Approchee)
    assert 2 <= len(res.choix) <= 3
    assert res.reformulation.endswith("Est-ce ce que vous cherchez ?")
    assert "circonscription" not in res.reformulation
    # Vérification que chaque choix est résoluble
    for ch in res.choix:
        r_verif = resoudre(SOCLE, ch.requete)
        assert hasattr(r_verif, "resultats") and len(r_verif.resultats) >= 1


def test_approchee_periode_absente_pauvrete():
    req = RequeteStructuree(
        intention="valeur",
        indicateur="jcvcajc.taux-de-pauvrete",
        zones=["SN"],
        periode=Periode(type="annee", valeur="2023"),
        confiance=1.0,
    )
    intr = Introuvable("periode_absente", "2023 non publié")
    res = proposer_approchee(
        SOCLE, req, intr, "Quel est le taux de pauvreté au Sénégal en 2023 ?", "fr"
    )
    assert isinstance(res, Approchee)
    assert 2 <= len(res.choix) <= 3
    # Les années les plus proches doivent contenir 2022
    annees = [ch.requete.periode.valeur for ch in res.choix]
    assert "2022" in annees
    for ch in res.choix:
        r_verif = resoudre(SOCLE, ch.requete)
        assert hasattr(r_verif, "resultats") and len(r_verif.resultats) >= 1


def test_approchee_periode_absente_chomage_futur():
    req = RequeteStructuree(
        intention="valeur",
        indicateur="dwibrlf",
        zones=["SN-KL"],
        periode=Periode(type="annee", valeur="2026"),
        confiance=1.0,
    )
    intr = Introuvable("periode_absente", "2026 non publié")
    res = proposer_approchee(SOCLE, req, intr, "Taux de chômage à Kaolack en 2026", "fr")
    assert isinstance(res, Approchee)
    assert 2 <= len(res.choix) <= 3
    annees = [ch.requete.periode.valeur for ch in res.choix]
    assert "2025" in annees
    for ch in res.choix:
        r_verif = resoudre(SOCLE, ch.requete)
        assert hasattr(r_verif, "resultats") and len(r_verif.resultats) >= 1


def test_approchee_zone_parente_pikine_electricite():
    req = RequeteStructuree(
        intention="valeur",
        indicateur="asongtc",
        zones=["SN-DK-PIKINE"],
        periode=Periode(type="derniere"),
        confiance=1.0,
    )
    intr = Introuvable("zone_non_couverte", "SN-DK-PIKINE non publié")
    res = proposer_approchee(
        SOCLE, req, intr, "Quel pourcentage des ménages ont l'électricité à Pikine ?", "fr"
    )
    assert isinstance(res, Approchee)
    assert len(res.choix) == 2
    zones_proposees = [ch.requete.zones[0] for ch in res.choix]
    assert "SN-DK" in zones_proposees
    assert "SN" in zones_proposees
    for ch in res.choix:
        r_verif = resoudre(SOCLE, ch.requete)
        assert hasattr(r_verif, "resultats") and len(r_verif.resultats) >= 1


def test_approchee_zone_parente_kaolack_criminalite_repli_periode():
    # iocwzud est national uniquement. Pour Kaolack, parent = SN.
    # Repli (b) : proposer SN sur 2 périodes pour faire 2 choix.
    req = RequeteStructuree(
        intention="valeur",
        indicateur="iocwzud",
        zones=["SN-KL"],
        periode=Periode(type="derniere"),
        confiance=1.0,
    )
    intr = Introuvable("zone_non_couverte", "SN-KL non publié")
    res = proposer_approchee(
        SOCLE, req, intr, "Quel est le taux de criminalité à Kaolack ?", "fr"
    )
    assert isinstance(res, Approchee)
    assert len(res.choix) == 2
    assert all(ch.requete.zones == ["SN"] for ch in res.choix)
    for ch in res.choix:
        r_verif = resoudre(SOCLE, ch.requete)
        assert hasattr(r_verif, "resultats") and len(r_verif.resultats) >= 1


def test_approchee_modalite_ambigue_voitures():
    req = RequeteStructuree(
        intention="valeur",
        indicateur="qbvttzc",
        zones=["SN-KD"],
        periode=Periode(type="derniere"),
        confiance=1.0,
    )
    res = proposer_approchee(SOCLE, req, None, "Nombre de voitures à Kolda", "fr")
    assert isinstance(res, Approchee)
    assert len(res.choix) == 2
    categories = [ch.requete.desagregation.get("catégories") for ch in res.choix]
    assert "TOTAL" in categories
    assert "VPP" in categories
    for ch in res.choix:
        r_verif = resoudre(SOCLE, ch.requete)
        assert hasattr(r_verif, "resultats") and len(r_verif.resultats) >= 1


def test_approchee_voitures_sans_le_filtre_ajoute_par_le_llm():
    # Le LLM range « voitures » dans la désagrégation (produit = voitures) : ce terme n'est pas une
    # catégorie publiée, il est retiré avant de proposer TOTAL et VPP (#116)
    req = RequeteStructuree(intention="valeur", indicateur="qbvttzc", zones=["SN-KD"],
                            periode=Periode(type="derniere"), desagregation={"produit": "voitures"},
                            confiance=0.9)
    res = proposer_approchee(SOCLE, req, None, "Nombre de voitures à Kolda", "fr")
    assert isinstance(res, Approchee)
    assert [ch.requete.desagregation for ch in res.choix] == [{"catégories": "TOTAL"}, {"catégories": "VPP"}]


def test_modalite_citee_sauf_si_categorie_deja_precisee():
    req = RequeteStructuree(intention="valeur", indicateur="qbvttzc", zones=["SN-KD"],
                            periode=Periode(type="derniere"), confiance=0.9)
    assert modalite_citee(req, "Nombre de voitures à Kolda") is not None
    assert modalite_citee(req, "Ñata woto ñoo nekk Kolda ?") is not None
    precise = req.model_copy(update={"desagregation": {"catégories": "VPP"}})
    assert modalite_citee(precise, "Nombre de voitures particulières à Kolda") is None
    assert modalite_citee(req.model_copy(update={"indicateur": "pvswjnd"}), "voitures") is None


def test_approchee_reformulation_fr_seulement():
    # V1.0 : FR seulement en attendant #25 (règle 6, décision 0009)
    req = RequeteStructuree(
        intention="valeur",
        indicateur="qbvttzc",
        zones=["SN-ZG"],
        periode=Periode(type="derniere"),
        confiance=1.0,
    )
    res = proposer_approchee(SOCLE, req, None, "Ñata voitures nio nek ziguinchor ?", "wo")
    assert isinstance(res, Approchee)
    assert res.reformulation.endswith("Est-ce ce que vous cherchez ?")
