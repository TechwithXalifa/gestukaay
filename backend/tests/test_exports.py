import csv
import io

import pytest
from fastapi.testclient import TestClient
from gestukaay_backend.app import app
from gestukaay_backend.exports import COLONNES

client = TestClient(app)


def _id(question: str) -> str:
    return client.post("/v1/ask", json={"question": question}).json()["reponse"]["id"]


def test_csv_au_schema_ef34():
    r = client.get(f"/v1/answers/{_id('Population de Dakar et de Thiès en 2023')}/export.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.content.startswith(b"\xef\xbb\xbf")  # BOM : Excel FR lit l'UTF-8
    lignes = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
    assert lignes[0] == COLONNES
    assert lignes[1][:5] == ["Population totale", "Dakar", "SN-DK", "2023", "4004426"]
    assert lignes[1][7].startswith("ANSD · RGPH-5") and "/r/" in lignes[1][10]
    assert len(lignes) == 3


def test_csv_virgule_decimale_en_option():
    rid = _id("Combien d'habitants à Thiès ?")
    r = client.get(f"/v1/answers/{rid}/export.csv?decimale=virgule")
    assert r.status_code == 200


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

