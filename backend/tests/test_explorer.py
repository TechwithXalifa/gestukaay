"""Catalogue, fiche indicateur et séries d'Explorer (contrat 1.4.0, décision 0023), sur le faux moteur."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_contracts.models import CatalogueResponse, FicheIndicateur, SeriesResponse
from gestukaay_engine import NonDisponible

client = TestClient(module_app.app)
PAUVRETE = "jcvcajc.taux-de-pauvrete"


def test_catalogue_et_filtres():
    tout = CatalogueResponse.model_validate(client.get("/v1/indicators").json())
    assert tout.total == 11 and len(tout.indicateurs) == 2
    filtre = client.get("/v1/indicators", params={"q": "pauvreté"}).json()
    assert filtre["total"] == 1 and filtre["indicateurs"][0]["code"] == PAUVRETE
    assert client.get("/v1/indicators", params={"domaine": "Santé"}).json()["total"] == 0
    assert client.get("/v1/indicators", params={"limite": 500}).status_code == 422


def test_fiche_et_indicateur_inconnu():
    f = FicheIndicateur.model_validate(client.get(f"/v1/indicators/{PAUVRETE}").json())
    assert f.source.libelle and f.citation.startswith("Source : ")
    r = client.get("/v1/indicators/inconnu")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/problem+json")


def test_series_absents_et_periode():
    r = client.get("/v1/series", params={"indicateur": PAUVRETE, "zones": "SN,SN-KD,SN-TH", "debut": "2019"})
    s = SeriesResponse.model_validate(r.json())
    assert [x.zone.code for x in s.series] == ["SN", "SN-KD"] and s.absents == ["SN-TH"]
    assert all(p.periode >= "2019" for x in s.series for p in x.points)  # rien d'interpolé, rien avant
    assert s.graphique and s.graphique.type == "courbe"


def test_series_zones_controlees():
    trop = "SN,SN-DK,SN-KD,SN-TH,SN-KL,SN-SL,SN-ZG"  # 7 zones
    assert client.get("/v1/series", params={"indicateur": PAUVRETE, "zones": trop}).status_code == 422
    assert client.get("/v1/series", params={"indicateur": PAUVRETE, "zones": " , "}).status_code == 422
    assert client.get("/v1/series", params={"indicateur": "inconnu", "zones": "SN"}).status_code == 404


def test_export_csv_des_series():
    r = client.get("/v1/series.csv", params={"indicateur": PAUVRETE, "zones": "SN,SN-DK", "decimale": "virgule"})
    assert r.status_code == 200
    lignes = r.content.decode("utf-8-sig").splitlines()
    assert lignes[0].startswith("indicateur;zone;code_zone;periode;valeur;unite")
    assert len(lignes) == 1 + 6  # 2 zones x 3 années publiées
    assert "SN-DK;2022;9,3;%" in r.text and "/explorer?indicateur=jcvcajc.taux-de-pauvrete&zones=SN,SN-DK" in r.text


def test_moteur_reel_pas_encore_disponible(monkeypatch):
    class _Reel:
        def catalogue(self, *a, **k):
            raise NonDisponible("catalogue")

        def fiche(self, *a, **k):
            raise NonDisponible("fiche")

        def series(self, *a, **k):
            raise NonDisponible("séries")

    monkeypatch.setattr(module_app, "moteur", _Reel())
    for url in ("/v1/indicators", f"/v1/indicators/{PAUVRETE}", f"/v1/series?indicateur={PAUVRETE}"):
        assert client.get(url).status_code == 503
