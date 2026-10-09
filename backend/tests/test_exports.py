import csv
import io

import pytest
from fastapi.testclient import TestClient
from gestukaay_backend.app import app
from gestukaay_backend.exports import COLONNES, NOTE_COMPARAISON

client = TestClient(app)


def _id(question: str) -> str:
    return client.post("/v1/ask", json={"question": question}).json()["reponse"]["id"]


def test_csv_au_schema_ef34():
    r = client.get(f"/v1/answers/{_id('Population de Dakar et de Thiès en 2023')}/export.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.content.startswith(b"\xff\xfe")  # BOM UTF-16 : Excel lit les accents et les colonnes
    lignes = list(csv.reader(io.StringIO(r.content.decode("utf-16")), delimiter="\t"))
    assert lignes[0] == COLONNES
    assert lignes[1][:5] == ["Population totale", "Dakar", "SN-DK", "2023", "4004426"]
    assert lignes[1][7].startswith("ANSD · RGPH-5") and "/r/" in lignes[1][10]
    assert len(lignes) == 3


def test_csv_reprend_les_regions_du_graphique():
    """Retour de recette : la page montre les 14 régions autour de Thiès, le CSV n'en donnait qu'une."""
    r = client.get(f"/v1/answers/{_id('Combien d’habitants à Thiès ?')}/export.csv")
    lignes = list(csv.reader(io.StringIO(r.content.decode("utf-16")), delimiter="\t"))[1:]
    assert len(lignes) == 14 and lignes[0][:3] == ["Population totale", "Thiès", "SN-TH"]
    assert lignes[0][9] != NOTE_COMPARAISON  # la valeur demandée garde sa note de périmètre
    autres = lignes[1:]
    assert {ligne[2] for ligne in autres} >= {"SN-DK", "SN-KE", "SN-SE"} and all(ligne[2] for ligne in autres)
    assert all(ligne[9] == NOTE_COMPARAISON and ligne[3] == "2023" and ligne[7] == lignes[0][7] for ligne in autres)


def test_csv_academie_sans_doublon_et_meme_ecriture():
    """Relecture KBD (#129), FR-003 : la réponse dit « académie de Kolda », le graphique « Kolda ».
    La zone demandée ne revient pas en comparaison, les autres s'écrivent « académie de … »."""
    from gestukaay_backend.exports import _comparaisons
    from gestukaay_contracts.models import (
        Graphique,
        PointGraphique,
        RefZone,
        ReponseExacte,
        SerieGraphique,
    )

    rep = ReponseExacte.model_validate(client.get(f"/v1/answers/{_id('Combien d’habitants à Thiès ?')}").json()["reponse"])
    r0 = rep.resultats[0].model_copy(update={"zone": RefZone(code="SN-IA-KOLDA", libelle="académie de Kolda",
                                                                  niveau="academie")})
    points = [PointGraphique(x=x, y=y, mise_en_evidence=x == "Kolda") for x, y in
              (("Kédougou", 118.4), ("Kolda", 93.8), ("Ziguinchor", 118.0))]
    rep = rep.model_copy(update={"resultats": [r0], "graphique": Graphique(
        type="barres_horizontales", titre="Taux brut de scolarisation par académie en 2025", unite="%",
        series=[SerieGraphique(nom="Taux brut de scolarisation", points=points)], pied="MEN")})
    assert _comparaisons(rep) == [("académie de Kédougou", "SN-IA-KEDOUGOU", 118.4),
                                  ("académie de Ziguinchor", "SN-IA-ZIGUINCHOR", 118.0)]


def test_csv_virgule_decimale_en_option():
    rid = _id("Combien d'habitants à Thiès ?")
    r = client.get(f"/v1/answers/{rid}/export.csv?decimale=virgule")
    assert r.status_code == 200


def test_csv_pour_excel_utf16_tabulations():
    """Excel l'ouvre en colonnes, accents compris, quelle que soit la langue de Windows (choix du 09/10)."""
    r = client.get(f"/v1/answers/{_id('Combien d’habitants à Thiès ?')}/export.csv")
    assert r.headers["content-type"] == "text/csv; charset=utf-16"
    assert r.content[:2] == b"\xff\xfe"  # BOM UTF-16 petit-boutiste
    premiere, deuxieme = r.content.decode("utf-16").splitlines()[:2]
    assert premiere.split("\t")[:3] == ["indicateur", "zone", "code_zone"]
    assert "\tThiès\tSN-TH\t" in deuxieme and ";" not in premiere


def test_pdf_une_page_a4():
    try:
        import fontTools.misc.bezierTools  # noqa: F401
    except ImportError:
        pytest.skip("fpdf2 bloqué sur ce poste : vérifié en CI et dans Docker")
    # Avec graphique (Thiès), deux valeurs (comparaison), projection : toujours une seule page
    for question in ("Combien d’habitants à Thiès ?", "Population de Dakar et de Thiès en 2023",
                     "Espérance de vie au Sénégal en 2035"):
        r = client.get(f"/v1/answers/{_id(question)}/export.pdf")
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF") and r.content.count(b"/Type /Page\n") <= 1


def test_pas_d_export_sans_valeur():
    r = client.get(f"/v1/answers/{_id('Population de la ville de Thiès en 2023')}/export.pdf")
    assert r.status_code == 409
    assert r.headers["content-type"].startswith("application/problem+json")


def test_mention_de_licence_jamais_supposee():
    """Décision 0016 §2 : licence publiée si le portail la donne, sinon on le dit (jamais « CC BY » inventé)."""
    from types import SimpleNamespace

    from gestukaay_backend.exports import mention_licence_donnees

    assert mention_licence_donnees([SimpleNamespace(licence="CC BY 4.0")]) == "Licence des données : CC BY 4.0"
    vide = mention_licence_donnees([SimpleNamespace(licence="")])
    assert "non précisée" in vide and "CC BY" not in vide

