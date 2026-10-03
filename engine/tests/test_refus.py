"""Tests du module de refus, motifs et suggestions proches (issue #13).

Socle synthétique : tourne en CI, sans le socle extrait.
"""

from datetime import date

from gestukaay_contracts.models import Periode, ReponseAucune, RequeteStructuree
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.refus import (
    MESSAGE_HORS_SOCLE_SUGGESTIONS,
    MESSAGE_INCOMPREHENSION,
    construire_reponse_aucune,
    derniere_annee_publiee,
    est_projection,
    obtenir_suggestions,
    refuser,
)
from gestukaay_engine.resolution import resoudre
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
        "dwibrlf",
        "jcvcajc",
        "tsghpfc",
        "ioxbglg",
        "asongtc",
    )
}

SOCLE = Socle(
    [
        # Population pvswjnd : séries observées 2023 et projections officielles jusqu'en 2038
        obs("pvswjnd", "SN", "2023", 18126390, sexe="Total", age="Total"),
        obs("pvswjnd", "SN-TH", "2023", 2463677, sexe="Total", age="Total"),
        obs("pvswjnd", "SN", "2035", 22000000, nature="projection", base="Projections 2023-2073"),
        obs("pvswjnd", "SN", "2038", 23500000, nature="projection", base="Projections 2023-2073"),
        # Chômage dwibrlf : jusqu'en 2025
        obs("dwibrlf", "SN", "2025", 20.4, sexe="TOTAL", âge="TOTAL"),
        obs("dwibrlf", "SN-KL", "2025", 37.2, sexe="TOTAL", âge="TOTAL"),
        # Pauvreté jcvcajc : 2022
        obs("jcvcajc.taux-de-pauvrete", "SN", "2022", 37.5),
        obs("jcvcajc.taux-de-pauvrete", "SN", "2019", 42.0),
        # Inflation tsghpfc : jusqu'en 2026
        obs("tsghpfc.indice-global", "SN", "2026", 112.5),
        obs("tsghpfc.indice-global", "SN", "2025", 108.0),
        # Prison ioxbglg
        obs("ioxbglg.nombre-de-personnes-emprisonnees", "SN", "2025", 15721, sexe="TOTAL", groupe_d_âge="Total"),
    ],
    SOURCES,
)


def test_derniere_annee_publiee():
    assert derniere_annee_publiee(SOCLE, "pvswjnd") == 2038
    assert derniere_annee_publiee(SOCLE, "dwibrlf") == 2025
    assert derniere_annee_publiee(SOCLE, "tsghpfc.indice-global") == 2026


def test_projection_regle_generique_sans_valeurs_en_dur():
    # FR-055 : Population en 2040 -> 2040 > 2026 et > 2038 -> True
    req_2040 = RequeteStructuree(
        intention="valeur",
        indicateur="pvswjnd",
        zones=["SN"],
        periode=Periode(type="annee", valeur="2040"),
        confiance=1.0,
    )
    est_proj, an = est_projection(SOCLE, req_2040, "Population du Sénégal en 2040")
    assert est_proj is True
    assert an == 2040

    # 2035 <= 2038 (publié dans le socle) -> pas une projection refusée
    req_2035 = RequeteStructuree(
        intention="valeur",
        indicateur="pvswjnd",
        zones=["SN"],
        periode=Periode(type="annee", valeur="2035"),
        confiance=1.0,
    )
    est_proj_35, an_35 = est_projection(SOCLE, req_2035, "Population du Sénégal en 2035")
    assert est_proj_35 is False
    assert an_35 == 2035

    # FR-056 : Chômage en 2030 -> 2030 > 2026 et > 2025 -> True
    req_2030 = RequeteStructuree(
        intention="valeur",
        indicateur="dwibrlf",
        zones=["SN"],
        periode=Periode(type="annee", valeur="2030"),
        confiance=1.0,
    )
    est_proj_chom, an_chom = est_projection(SOCLE, req_2030, "Quel sera le taux de chômage en 2030 ?")
    assert est_proj_chom is True
    assert an_chom == 2030

    # FR-057 : Inflation en 2027 -> 2027 > 2026 et > 2026 -> True
    req_2027 = RequeteStructuree(
        intention="valeur",
        indicateur="tsghpfc.indice-global",
        zones=["SN"],
        periode=Periode(type="annee", valeur="2027"),
        confiance=1.0,
    )
    est_proj_inf, an_inf = est_projection(SOCLE, req_2027, "Quelle sera l'inflation en 2027 ?")
    assert est_proj_inf is True
    assert an_inf == 2027

    # Année passée non publiée (ex. 2023 pour chômage non publié au national) -> pas une projection
    req_passee = RequeteStructuree(
        intention="valeur",
        indicateur="dwibrlf",
        zones=["SN"],
        periode=Periode(type="annee", valeur="2022"),
        confiance=1.0,
    )
    est_proj_p, _ = est_projection(SOCLE, req_passee, "Taux de chômage en 2022")
    assert est_proj_p is False


def test_refus_projection_fr055_population():
    comp = Comprehension(None)
    comprise = comp.comprendre("Population du Sénégal en 2040")
    ref = refuser(SOCLE, comprise, "Population du Sénégal en 2040", "fr")
    assert ref.motif == "projection"
    assert "Gëstukaay ne fait pas de prévisions." in ref.message
    assert "projections officielles de population" in ref.message
    assert len(ref.suggestions) == 1
    assert ref.suggestions[0].indicateur.code == "pvswjnd"
    assert ref.suggestions[0].question_suggeree == "Combien d'habitants au Sénégal ?"


def test_refus_projection_fr056_chomage():
    comp = Comprehension(None)
    comprise = comp.comprendre("Quel sera le taux de chômage en 2030 ?")
    ref = refuser(SOCLE, comprise, "Quel sera le taux de chômage en 2030 ?", "fr")
    assert ref.motif == "projection"
    assert "Gëstukaay ne fait pas de prévisions." in ref.message
    assert len(ref.suggestions) == 1
    assert ref.suggestions[0].indicateur.code == "dwibrlf"


def test_refus_projection_demain_ne_doit_pas_devenir_projection():
    # FR-060 : « Quel temps fera-t-il demain à Dakar ? »
    # « demain » ne doit pas devenir une projection : FR-060 est hors socle
    comp = Comprehension(None)
    comprise = comp.comprendre("Quel temps fera-t-il demain à Dakar ?")
    ref = refuser(SOCLE, comprise, "Quel temps fera-t-il demain à Dakar ?", "fr")
    assert ref.motif == "hors_socle"
    assert ref.motif != "projection"
    assert ref.message == MESSAGE_HORS_SOCLE_SUGGESTIONS


def test_refus_hors_socle_lieu_inconnu_paris():
    # FR-061 : Lieu inconnu (Paris) absent de rattachements.csv -> hors_socle direct
    comp = Comprehension(None)
    comprise = comp.comprendre("Combien d'habitants à Paris ?")
    assert "Paris" in comprise.lieux_inconnus
    ref = refuser(SOCLE, comprise, "Combien d'habitants à Paris ?", "fr")
    assert ref.motif == "hors_socle"
    assert ref.message == MESSAGE_HORS_SOCLE_SUGGESTIONS
    # Suggestions vérifiées au niveau national SN
    assert len(ref.suggestions) >= 1
    for s in ref.suggestions:
        r = resoudre(SOCLE, RequeteStructuree(intention="valeur", indicateur=s.indicateur.code, zones=["SN"], confiance=1.0))
        assert hasattr(r, "resultats") and len(r.resultats) >= 1


def test_refus_hors_socle_sujets_absents():
    # Sujets hors socle du jeu de test
    questions_hors_socle = [
        "Combien de mosquées y a-t-il à Touba ?",  # FR-058
        "Qui est le président du Sénégal ?",  # FR-059
        "Combien gagne un chauffeur de taxi à Dakar ?",  # FR-062
        "Écris-moi un poème sur la Casamance",  # FR-063
        "Combien de vaches a mon voisin ?",  # FR-066
        "Combien de Sénégalais sont partis en pèlerinage à La Mecque en 2024 ?",  # FR-072
    ]
    comp = Comprehension(None)
    for q in questions_hors_socle:
        comprise = comp.comprendre(q)
        ref = refuser(SOCLE, comprise, q, "fr")
        assert ref.motif == "hors_socle", f"Échec sur {q}"
        assert ref.message == MESSAGE_HORS_SOCLE_SUGGESTIONS
        assert 1 <= len(ref.suggestions) <= 3


def test_contre_exemple_serere_ne_suggere_jamais_prison():
    # Contre-exemple obligatoire : « personnes parlent sérère » ne doit JAMAIS
    # suggérer « personnes emprisonnées ».
    comp = Comprehension(None)
    q = "Combien de personnes parlent sérère au Sénégal ?"  # FR-071
    comprise = comp.comprendre(q)
    ref = refuser(SOCLE, comprise, q, "fr")

    assert ref.motif == "hors_socle"
    assert len(ref.suggestions) > 0
    codes_suggeres = [s.indicateur.code for s in ref.suggestions]
    libelles_suggeres = [s.indicateur.libelle for s in ref.suggestions]

    # Vérification stricte : aucun lien avec la prison
    assert "ioxbglg.nombre-de-personnes-emprisonnees" not in codes_suggeres
    assert not any("prison" in c.lower() for c in codes_suggeres)
    assert not any("prison" in lib.lower() or "emprisonn" in lib.lower() for lib in libelles_suggeres)

    # Repli sur les 3 phares P1
    assert "pvswjnd" in codes_suggeres


def test_incomprehension_charabia_et_bavardage():
    comp = Comprehension(None)
    for q in ["asdkjh qwe", "euh bon voilà quoi"]:
        comprise = comp.comprendre(q)
        assert comprise.incomprehensible is True
        ref = refuser(SOCLE, comprise, q, "fr")
        assert ref.motif == "incomprehension"
        assert ref.message == MESSAGE_INCOMPREHENSION
        assert ref.suggestions == []
        assert ref.requete is None


def test_suggestions_resolution_verifiee():
    comp = Comprehension(None)
    comprise = comp.comprendre("Combien de personnes parlent sérère au Sénégal ?")
    suggs = obtenir_suggestions(SOCLE, comprise, "SN")
    assert len(suggs) == 3
    # Chaque suggestion a été vérifiée par la résolution dans le socle
    for s in suggs:
        req = RequeteStructuree(intention="valeur", indicateur=s.indicateur.code, zones=["SN"], confiance=1.0)
        res = resoudre(SOCLE, req)
        assert hasattr(res, "resultats") and len(res.resultats) >= 1
        assert s.question_suggeree.endswith(" ?")


def test_modele_reponse_aucune_contrat():
    comp = Comprehension(None)
    q = "Combien de personnes parlent sérère au Sénégal ?"
    comprise = comp.comprendre(q)
    ref = refuser(SOCLE, comprise, q, "fr")

    reponse = construire_reponse_aucune(ref, q, version_socle="2026.10.0")
    assert isinstance(reponse, ReponseAucune)
    assert reponse.issue == "aucune"
    assert reponse.motif == "hors_socle"
    assert reponse.langue == "fr"  # Règle 6 : FR seulement
    assert reponse.message == MESSAGE_HORS_SOCLE_SUGGESTIONS
    assert len(reponse.suggestions) == 3
    # Sérialisation Pydantic stricte (extra="forbid")
    json_str = reponse.model_dump_json()
    assert "hors_socle" in json_str
