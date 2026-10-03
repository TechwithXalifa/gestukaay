"""Gabarits FR (#16, décision 0014). Résultats synthétiques : tourne en CI, sans le socle."""

import re
from datetime import date

import pytest
from gestukaay_contracts.models import PeriodeResolue, RefIndicateur, RefZone, Resultat, Source
from gestukaay_engine.gabarits import (
    FINE,
    avec_unite,
    citation,
    explication,
    formater,
    gabarits,
    note_perimetre,
    periode_en_lettres,
    zone_en_lettres,
)
from gestukaay_socle.indicateurs import indicateurs

SOURCE = Source(producteur="ANSD", operation="RGPH-5", titre="Population", date_publication=date(2023, 10, 31),
                licence="", url="https://x", libelle="ANSD · RGPH-5")


def res(code, zone, niveau, periode, valeur, unite, nature="observee", base=None, **desag):
    return Resultat(indicateur=RefIndicateur(code=code, libelle=code), zone=RefZone(code=zone, libelle=zone, niveau=niveau),
                    periode=PeriodeResolue(valeur=periode, libelle=periode), desagregation=desag or None,
                    valeur=valeur, valeur_affichee=formater(valeur, unite)[0], unite=unite, source=SOURCE,
                    observation_id="o", nature=nature, base_projection=base)


def phrases(texte):
    return [p for p in re.split(r"(?<=[.!?])\s+(?=[A-ZÉ0-9])", texte) if p]


def test_nombres():
    assert formater(2463677, "habitants") == (f"2{FINE}463{FINE}677", False)
    assert formater(25.7, "%") == ("25,7", False)
    assert formater(391.145833, "FCFA le kg") == ("391", True)  # arrondi signalé
    assert formater(93.80645, "%") == ("93,8", True)
    assert formater(13.0, "%") == ("13", False)  # jamais plus de décimales que publiées
    assert formater(0.3, "indice de 0 à 1") == ("0,3", False)
    assert avec_unite("25,7", "%") == f"25,7{FINE}%" and avec_unite("74,6", "ans") == "74,6 ans"


def test_zones_et_periodes_en_lettres():
    assert zone_en_lettres("SN") == {"dans": "au Sénégal", "sujet": "Le Sénégal", "de": "du Sénégal"}
    assert zone_en_lettres("SN-TH")["dans"] == "dans la région de Thiès"
    assert zone_en_lettres("SN-TH-MBOUR")["de"] == "du département de Mbour"
    assert zone_en_lettres("SN-IA-KOLDA")["sujet"] == "L'académie de Kolda"
    assert periode_en_lettres("2026-03") == "en mars 2026" and periode_en_lettres("2024-T1") == "au 1er trimestre 2024"


def test_phrase_naturelle_p1_et_derniere_donnee():
    r = res("pvswjnd", "SN-TH", "region", "2023", 2463677, "habitants")
    assert explication([r], derniere=True) == (
        f"La région de Thiès compte 2{FINE}463{FINE}677 habitants en 2023, dernière donnée publiée.")


def test_position_relative_pour_un_taux_pas_pour_un_effectif():
    r = res("dwibrlf", "SN-KL", "region", "2025", 37.2, "%")
    n = res("dwibrlf", "SN", "pays", "2025", 20.4, "%")
    texte = explication([r], nationaux={"dwibrlf": n})
    assert texte.endswith(f"C'est plus que la valeur nationale (20,4{FINE}% en 2025).")
    pop = res("pvswjnd", "SN-TH", "region", "2023", 2463677, "habitants")
    assert "nationale" not in explication([pop], nationaux={"pvswjnd": res("pvswjnd", "SN", "pays", "2023", 1, "habitants")})


def test_forme_neutre_hors_p1_et_notes():
    code = next(c for c, x in indicateurs().items() if x.priorite == "P3" and x.unite == "%")
    texte = explication([res(code, "SN", "pays", "2020", 12.345, "%", nature="estimation", base="Rétropolation")])
    assert texte.startswith(indicateurs()[code].libelle_fr) and ": 12,3" in texte
    assert "estimation (Rétropolation)" in texte and "valeur arrondie" in texte


def test_projection_signalee():
    r = res("pexioke.esperance-de-vie-a-la-naissance", "SN", "pays", "2035", 74.6, "ans", "projection",
            "Projections démographiques RGPHAE 2013")
    assert "projection officielle (ANSD, Projections démographiques RGPHAE 2013)" in explication([r])


def test_comparaison():
    a = res("dwibrlf", "SN-DK", "region", "2024", 15.8, "%")
    b = res("dwibrlf", "SN-TH", "region", "2024", 20.6, "%")
    texte = explication([a, b])
    assert "en 2024 :" in texte and "la plus élevée est celle de la région de Thiès" in texte


@pytest.mark.parametrize("code", sorted(c for c, x in indicateurs().items() if x.priorite == "P1"))
def test_chaque_gabarit_p1_se_remplit(code):
    """Les 27 gabarits P1 : trous valides, 1 à 3 phrases, pas d'accolade oubliée (§5.4)."""
    assert code in gabarits()
    x = indicateurs()[code]
    r = res(code, "SN-DK", "region", "2023", 12.34, x.unite_affichee or x.unite, sexe="Féminin")
    texte = explication([r], derniere=True, nationaux={code: res(code, "SN", "pays", "2023", 10.0, r.unite)})
    assert "{" not in texte and "}" not in texte
    assert 1 <= len(phrases(texte)) <= 3, texte


def test_note_de_perimetre():
    assert note_perimetre(res("feujxob.riz-brise-ordinaire-au-detail", "SN-DK", "region", "2026-03", 309, "FCFA le kg")) \
        == "Prix relevés dans l'agglomération de Dakar, pas dans toute la région."
    assert note_perimetre(res("pvswjnd", "SN-TH", "region", "2023", 1, "habitants")) == "Région administrative, pas la ville."
    assert note_perimetre(res("pvswjnd", "SN", "pays", "2023", 1, "habitants")) is None


def test_citation_ef35():
    r = res("pvswjnd", "SN-TH", "region", "2023", 2463677, "habitants")
    assert citation(r, date(2026, 10, 3), "https://gestukaay.sn/r/abc") == (
        "Source : ANSD, RGPH-5 (2023), publié le 31 octobre 2023. Consulté via Gëstukaay le 3 octobre 2026, "
        "https://gestukaay.sn/r/abc.")
