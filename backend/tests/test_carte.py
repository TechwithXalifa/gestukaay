"""Carte des 14 régions (Explorer, vue « Carte »), sur le faux moteur : Dakar et Kolda publient le taux de pauvreté."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend import securite
from gestukaay_backend.carte import CarteResponse, carte, regions
from gestukaay_engine.fake import MoteurFactice

client = TestClient(module_app.app)
PAUVRETE = "jcvcajc.taux-de-pauvrete"


def test_periode_par_defaut_valeurs_et_absents():
    r = CarteResponse.model_validate(client.get("/v1/carte", params={"indicateur": PAUVRETE}).json())
    assert r.periode == "2022" and r.periodes == ["2022", "2019", "2011"]
    # De la plus haute à la plus basse ; les douze autres régions signalées, jamais estimées
    assert [(v.region, v.valeur) for v in r.valeurs] == [("SN-KD", 62.5), ("SN-DK", 9.3)]
    assert len(r.absents) == 12 and "SN-TH" in r.absents
    assert r.ensemble and r.ensemble.valeur == 37.5 and r.sources


def test_periode_choisie():
    r = client.get("/v1/carte", params={"indicateur": PAUVRETE, "periode": "2011"}).json()
    assert [v["valeur"] for v in r["valeurs"]] == [76.6, 26.1] and r["libelle_periode"] == "2011"
    vide = client.get("/v1/carte", params={"indicateur": PAUVRETE, "periode": "1990"}).json()
    assert vide["valeurs"] == [] and len(vide["absents"]) == 14 and vide["ensemble"] is None


def test_indicateur_inconnu():
    assert client.get("/v1/carte", params={"indicateur": "inconnu"}).status_code == 404
    assert securite.groupe("/v1/carte") == "explorer"


class _TroisQuarts(MoteurFactice):
    """Kolda publie aussi 2025, seule : 2025 ne doit pas l'emporter sur 2022, publiée par les deux régions."""

    def series(self, indicateur, zones, debut=None, fin=None):
        r = super().series(indicateur, zones, debut, fin)
        series = []
        for s in r.series:
            if s.zone.code == "SN-KD":
                dernier = s.points[-1].model_copy(update={"periode": "2025", "libelle": "2025", "valeur": 60.0})
                s = s.model_copy(update={"points": [*s.points, dernier]})
            series.append(s)
        return r.model_copy(update={"series": series})


def test_periode_par_defaut_publiee_par_la_plupart_des_regions():
    r = carte(_TroisQuarts(), PAUVRETE)
    assert r.periode == "2022" and r.periodes[0] == "2025"


def test_quatorze_regions_lues_par_paquets_de_six():
    appels = []

    class Compteur(MoteurFactice):
        def series(self, indicateur, zones, debut=None, fin=None):
            appels.append(len(zones))
            return super().series(indicateur, zones, debut, fin)

    carte(Compteur(), PAUVRETE)
    assert len(regions()) == 14 and max(appels) <= 6 and sum(appels) == 15  # 14 régions et le Sénégal
