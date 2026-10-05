"""Tests unitaires et d'intégration du benchmark et de l'invariant (issue #19).

Vérifie :
  - L'absence de fausse alerte sur des réponses réelles valides (arrondis, espaces,
    pourcentages, modalités d'âge, ordonnancement, périodes).
  - La détection infaillible des 4 types de violations de l'invariant (tolérance zéro) :
      (a) Resultat falsifié (observation_id inconnu ou valeur modifiée) ;
      (b) Point de graphique inventé ;
      (c) Nombre dans l'explication non sourcé par la liste blanche ;
      (d) Chiffre statistique apparu dans une approchée ou un refus.
  - La conformité des calculs d'exactitude (sourcée + citation) et de refus pertinent.
"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from gestukaay_contracts.models import (
    AskResponse,
    Choix,
    Graphique,
    PointGraphique,
    RefIndicateur,
    RefZone,
    ReponseApprochee,
    ReponseAucune,
    ReponseExacte,
    RequeteStructuree,
    Resultat,
    SerieGraphique,
    Source,
)
from gestukaay_engine.socle import Observation, Socle, SourceJeu
from gestukaay_socle.indicateurs import Indicateur

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "mesure" / "scripts"))

from benchmark import (
    extraire_nombres,
    normaliser_espace,
    verifier_exactitude_reponse,
    verifier_invariant_reponse,
    verifier_refus_reponse,
)

# ---------------------------------------------------------------------------
# Fixtures de test synthétiques
# ---------------------------------------------------------------------------


@pytest.fixture
def socle_test() -> Socle:
    obs = [
        Observation(
            id="obs-001",
            indicateur="pvswjnd",
            zone="SN-TH",
            zone_presumee=False,
            periode="2023",
            desagregation=(("age", "Total"), ("sexe", "Total")),
            valeur=2463677.0,
            unite="habitants",
            echelle="",
            source_id="src-ansd",
            nature="observee",
            base_projection="",
        ),
        Observation(
            id="obs-002",
            indicateur="pvswjnd",
            zone="SN-DK",
            zone_presumee=False,
            periode="2023",
            desagregation=(("age", "Total"), ("sexe", "Total")),
            valeur=4004426.0,
            unite="habitants",
            echelle="",
            source_id="src-ansd",
            nature="observee",
            base_projection="",
        ),
        Observation(
            id="obs-003",
            indicateur="dwibrlf",
            zone="SN",
            zone_presumee=False,
            periode="2025",
            desagregation=(("age", "15-24 ans"), ("sexe", "TOTAL")),
            valeur=25.7,
            unite="%",
            echelle="",
            source_id="src-ansd",
            nature="projection",
            base_projection="Projections 2023-2073",
        ),
    ]
    sources = {
        "src-ansd": SourceJeu(
            id="src-ansd",
            producteur="ANSD",
            organisme="ANSD",
            titre="RGPH-5",
            date_publication=date(2023, 10, 31),
            licence="CC BY 4.0",
            url="https://ansd.sn",
        )
    }
    return Socle(obs, sources, version="test-2026")


@pytest.fixture
def obs_par_id(socle_test: Socle) -> dict[str, Observation]:
    return {o.id: o for obs in socle_test._par_indicateur.values() for o in obs}


@pytest.fixture
def inds_test() -> dict[str, Indicateur]:
    from gestukaay_socle.indicateurs import indicateurs

    return indicateurs()


def reponse_exacte_valide() -> AskResponse:
    src = Source(
        producteur="ANSD",
        operation="RGPH-5",
        titre="Recensement Général",
        date_publication=date(2023, 10, 31),
        licence="CC BY 4.0",
        url="https://ansd.sn",
        libelle="ANSD · RGPH-5 · publié le 31 octobre 2023",
    )
    res = Resultat(
        indicateur=RefIndicateur(code="pvswjnd", libelle="Population (RGPH-5)"),
        zone=RefZone(code="SN-TH", libelle="Thiès", niveau="region"),
        periode={"valeur": "2023", "libelle": "2023"},  # type: ignore[arg-type]
        desagregation={"age": "Total", "sexe": "Total"},
        valeur=2463677.0,
        valeur_affichee="2 463 677",
        unite="habitants",
        source=src,
        observation_id="obs-001",
        mise_en_evidence=True,
        nature="observee",
    )
    graph = Graphique(
        type="barres_horizontales",
        titre="Population en 2023",
        unite="habitants",
        series=[
            SerieGraphique(
                nom="Population",
                points=[PointGraphique(x="Thiès", y=2463677.0, mise_en_evidence=True)],
            )
        ],
        pied="Source : ANSD, RGPH-5 · gestukaay",
    )
    return AskResponse(
        reponse=ReponseExacte(
            id="abc123",
            url="https://gestukaay.sn/r/abc123",
            question="Combien d'habitants à Thiès ?",
            langue="fr",
            cree_le=datetime.now(UTC),
            version_socle="test-2026",
            intention="valeur",
            resultats=[res],
            explication="La région de Thiès compte 2 463 677 habitants en 2023, dernière donnée publiée.",
            periode_par_defaut=True,
            citation="Source : ANSD, RGPH-5, publié le 31 octobre 2023.",
            graphique=graph,
        )
    )


# ---------------------------------------------------------------------------
# Tests de l'invariant : cas nominaux (pas de fausse alerte)
# ---------------------------------------------------------------------------


def test_invariant_reponse_exacte_valide_sans_fausse_alerte(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    q = {
        "id": "FR-001",
        "question": "Combien d'habitants à Thiès ?",
        "periode": "2023",
        "issue_attendue": "exacte",
    }
    rep = reponse_exacte_valide()
    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert len(viols) == 0, f"Fausses alertes détectées : {[v.message for v in viols]}"


def test_invariant_avec_modalites_desagregation_et_arrondi(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Vérifie que les modalités comme '15-24 ans' et les pourcentages ne déclenchent pas d'alerte."""
    q = {
        "id": "FR-002",
        "question": "Quel est le taux de chômage des jeunes de 15 à 24 ans ?",
        "periode": "2025",
        "issue_attendue": "exacte",
    }
    src = Source(
        producteur="ANSD",
        operation="Enquête Emploi",
        titre="Emploi",
        date_publication=date(2025, 1, 15),
        licence="CC BY 4.0",
        url="https://ansd.sn",
        libelle="ANSD · Enquête Emploi 2025",
    )
    res = Resultat(
        indicateur=RefIndicateur(code="dwibrlf", libelle="Taux de chômage"),
        zone=RefZone(code="SN", libelle="Sénégal", niveau="pays"),
        periode={"valeur": "2025", "libelle": "2025"},  # type: ignore[arg-type]
        desagregation={"age": "15-24 ans", "sexe": "TOTAL"},
        valeur=25.7,
        valeur_affichee="25,7",
        unite="%",
        source=src,
        observation_id="obs-003",
        mise_en_evidence=True,
        nature="projection",
        base_projection="Projections 2023-2073",
    )
    rep = AskResponse(
        reponse=ReponseExacte(
            id="def456",
            url="https://gestukaay.sn/r/def456",
            question=q["question"],
            langue="fr",
            cree_le=datetime.now(UTC),
            version_socle="test-2026",
            intention="valeur",
            resultats=[res],
            explication=(
                "Le taux de chômage (15-24 ans) est de 25,7 % au Sénégal en 2025. "
                "Il s'agit d'une projection officielle (ANSD, Projections 2023-2073)."
            ),
            periode_par_defaut=False,
            citation="Source : ANSD, Enquête Emploi 2025.",
        )
    )
    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert len(viols) == 0, f"Fausses alertes : {[v.message for v in viols]}"


# ---------------------------------------------------------------------------
# Tests de détection des violations (injections de chiffres faux)
# ---------------------------------------------------------------------------


def test_invariant_detecte_observation_id_inconnu(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Volet (a) : un observation_id qui n'existe pas dans le socle doit échouer."""
    q = {"id": "FR-001", "question": "Combien ?", "periode": "2023"}
    rep = reponse_exacte_valide()
    # Injection d'un faux observation_id
    rep.reponse.resultats[0].observation_id = "obs-fantome-999"  # type: ignore[union-attr]

    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "a" and "hors socle" in v.message for v in viols)


def test_invariant_detecte_valeur_resultat_discordante(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Volet (a) : la valeur servie diffère de celle enregistrée dans le socle."""
    q = {"id": "FR-001", "question": "Combien ?", "periode": "2023"}
    rep = reponse_exacte_valide()
    # Altération de la valeur réelle 2463677.0 -> 3000000.0
    rep.reponse.resultats[0].valeur = 3000000.0  # type: ignore[union-attr]

    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "a" and "socle" in v.message for v in viols)


def test_invariant_detecte_point_graphique_falsifie(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Volet (b) : un point de graphique avec une valeur y inventée."""
    q = {"id": "FR-001", "question": "Combien ?", "periode": "2023"}
    rep = reponse_exacte_valide()
    # Faux point graphique
    rep.reponse.graphique.series[0].points.append(  # type: ignore[union-attr]
        PointGraphique(x="Kolda", y=999999.0)
    )

    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "b" and "absent du socle" in v.message for v in viols)


def test_invariant_detecte_barre_thies_avec_population_dakar(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Volet (b) : la barre 'Thiès' avec la population de Dakar (4 004 426) doit être détectée."""
    q = {"id": "FR-001", "question": "Combien d'habitants à Thiès ?", "periode": "2023"}
    rep = reponse_exacte_valide()
    # Barre 'Thiès' avec la population réelle de Dakar au lieu de Thiès
    rep.reponse.graphique.series[0].points = [  # type: ignore[union-attr]
        PointGraphique(x="Thiès", y=4004426.0, mise_en_evidence=True)
    ]
    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "b" and "point barre" in v.message for v in viols)


def test_invariant_detecte_barre_zone_inconnue(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Volet (b) : un libellé de barre non rattaché à une zone du référentiel doit être détecté."""
    q = {"id": "FR-001", "question": "Combien d'habitants à Thiès ?", "periode": "2023"}
    rep = reponse_exacte_valide()
    rep.reponse.graphique.series[0].points = [  # type: ignore[union-attr]
        PointGraphique(x="ZoneInexistante", y=2463677.0, mise_en_evidence=True)
    ]
    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "b" and "ne correspond à aucune zone" in v.message for v in viols)


def test_invariant_detecte_chiffre_invente_dans_explication(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Volet (c) : un chiffre halluciné apparaît dans l'explication."""
    q = {"id": "FR-001", "question": "Combien ?", "periode": "2023"}
    rep = reponse_exacte_valide()
    # Injection d'un pourcentage ou chiffre inventé
    rep.reponse.explication = (  # type: ignore[union-attr]
        "La région de Thiès compte 2 463 677 habitants en 2023, avec un taux inventé de 48,9 %."
    )

    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "c" and "48,9" in v.message for v in viols)


def test_invariant_detecte_chiffre_court_soit_3_fois_plus(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Volet (c) : 'Soit 3 fois plus.' ajouté à l'explication doit produire une violation."""
    q = {"id": "FR-001", "question": "Combien d'habitants à Thiès ?", "periode": "2023"}
    rep = reponse_exacte_valide()
    # 'Soit 3 fois plus.' ajouté à l'explication (teste la suppression de l'exception 1,2,3,4)
    rep.reponse.explication = (  # type: ignore[union-attr]
        "La région de Thiès compte 2 463 677 habitants en 2023. Soit 3 fois plus."
    )
    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "c" and "'3'" in v.message for v in viols)


@pytest.mark.parametrize("morceau", ["2", "463", "677"])
def test_invariant_detecte_un_morceau_de_nombre_affiche(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
    morceau: str,
):
    """Volet (c) : « 2 463 677 » est autorisé, pas ses morceaux (« Soit 2 fois plus. »)."""
    q = {"id": "FR-001", "question": "Combien d'habitants à Thiès ?", "periode": "2023"}
    rep = reponse_exacte_valide()
    rep.reponse.explication = (  # type: ignore[union-attr]
        f"La région de Thiès compte 2 463 677 habitants en 2023. Soit {morceau} fois plus."
    )
    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "c" and f"'{morceau}'" in v.message for v in viols)


def test_invariant_detecte_valeur_numerique_dans_approchee(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Volet (d) : aucune valeur numérique statistique autorisée dans une réponse approchée."""
    q = {"id": "FR-047", "question": "Population Kaolack ?", "issue_attendue": "approchee"}
    req = RequeteStructuree(
        intention="valeur",
        indicateur="pvswjnd",
        zones=["SN-TH"],
        confiance=0.8,
    )
    rep = AskResponse(
        reponse=ReponseApprochee(
            id="app123",
            url="https://gestukaay.sn/r/app123",
            question=q["question"],
            langue="fr",
            cree_le=datetime.now(UTC),
            version_socle="test-2026",
            reformulation="Voici les chiffres demandés : il y a 500 personnes.",  # Interdit !
            choix=[
                Choix(id="1", libelle="Option Thiès en 2023", requete=req),
                Choix(id="2", libelle="Option Dakar en 2023", requete=req),
            ],
        )
    )
    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "d" and "500" in v.message for v in viols)


def test_invariant_detecte_valeur_numerique_dans_refus(
    socle_test: Socle,
    obs_par_id: dict[str, Observation],
    inds_test: dict[str, Indicateur],
):
    """Volet (d) : aucune valeur numérique statistique autorisée dans un message de refus."""
    q = {
        "id": "FR-060",
        "question": "Population en 2099 ?",
        "issue_attendue": "aucune",
        "motif": "projection",
    }
    rep = AskResponse(
        reponse=ReponseAucune(
            id="ref123",
            url="https://gestukaay.sn/r/ref123",
            question=q["question"],
            langue="fr",
            cree_le=datetime.now(UTC),
            version_socle="test-2026",
            motif="projection",
            message="Gëstukaay ne fait pas de prévisions. Cependant la valeur estimée est 42.",  # Interdit !
            suggestions=[],
        )
    )
    viols = verifier_invariant_reponse(q, rep, socle_test, obs_par_id, inds_test, {})
    assert any(v.volet == "d" and "42" in v.message for v in viols)


# ---------------------------------------------------------------------------
# Tests des métriques (Exactitude et Refus pertinent)
# ---------------------------------------------------------------------------


def test_evaluation_exactitude_succes(socle_test: Socle):
    q = {
        "id": "FR-001",
        "question": "Combien d'habitants à Thiès ?",
        "periode": "2023",
        "valeurs_attendues": "SN-TH=2463677",
        "periode_par_defaut": "oui",
        "type": "simple",
    }
    rep = reponse_exacte_valide()
    ok_val, ok_src, detail = verifier_exactitude_reponse(q, rep, socle_test)
    assert ok_val is True
    assert ok_src is True
    assert "conformes" in detail


def test_evaluation_exactitude_nombre_avec_son_taux_compagnon(socle_test: Socle):
    """0024 : l'exactitude porte sur le nombre demandé ; le taux compagnon n'est pas un écart."""
    q = {"id": "WO-002", "question": "Ñi amul ligéey ci Senegaal ?", "periode": "2026-T1",
         "valeurs_attendues": "SN=1590818", "periode_par_defaut": "oui", "type": "simple"}
    rep = reponse_exacte_valide()
    r0 = rep.reponse.resultats[0]  # type: ignore[union-attr]
    nombre = r0.model_copy(update={
        "indicateur": RefIndicateur(code="muhgux.population-au-chomage", libelle="Population au chômage"),
        "zone": RefZone(code="SN", libelle="Sénégal", niveau="pays"),
        "periode": r0.periode.model_copy(update={"valeur": "2026-T1"}), "valeur": 1590818.0})
    taux = nombre.model_copy(update={
        "indicateur": RefIndicateur(code="muhgux.taux-de-chomage", libelle="Taux de chômage"), "valeur": 22.9})
    rep.reponse.resultats = [nombre, taux]  # type: ignore[union-attr]
    ok_val, _, detail = verifier_exactitude_reponse(q, rep, socle_test)
    assert ok_val is True, detail
    rep.reponse.resultats = [nombre, taux.model_copy(update={  # type: ignore[union-attr]
        "indicateur": RefIndicateur(code="muhgux.taux-dactivite", libelle="Taux d'activité")})]
    assert verifier_exactitude_reponse(q, rep, socle_test)[0] is False  # un autre indicateur reste un écart


def test_evaluation_exactitude_echec_si_non_sourcee(socle_test: Socle):
    """Une réponse avec la bonne valeur mais sans citation échoue l'exactitude (§12.1)."""
    q = {
        "id": "FR-001",
        "question": "Combien d'habitants à Thiès ?",
        "periode": "2023",
        "valeurs_attendues": "SN-TH=2463677",
        "type": "simple",
    }
    rep = reponse_exacte_valide()
    rep.reponse.citation = ""  # Manque la citation requise

    ok_val, ok_src, _ = verifier_exactitude_reponse(q, rep, socle_test)
    assert ok_val is True
    assert ok_src is False  # Invalide car non sourcée


def test_evaluation_refus_pertinent():
    q = {"id": "FR-063", "motif": "hors_socle"}
    rep = AskResponse(
        reponse=ReponseAucune(
            id="ref001",
            url="https://gestukaay.sn/r/ref001",
            question="Question hors socle ?",
            langue="fr",
            cree_le=datetime.now(UTC),
            version_socle="test-2026",
            motif="hors_socle",
            message="Cette donnée n'existe pas dans les publications de l'ANSD que nous couvrons.",
            suggestions=[],
        )
    )
    ok_refus, detail = verifier_refus_reponse(q, rep)
    assert ok_refus is True
    assert "conforme" in detail


# ---------------------------------------------------------------------------
# Utilitaires de normalisation
# ---------------------------------------------------------------------------


def test_extraire_nombres_et_normalisation():
    texte = "En 2023, le taux est de 25,7 % (soit 4 004 426 habitants)."
    nums = extraire_nombres(texte)
    assert "2023" in nums
    assert "25,7" in nums
    assert "4 004 426" in nums
    assert normaliser_espace("1 000 FCFA") == "1 000 FCFA"
