"""« Ma région en chiffres », sur le faux moteur : seul le taux de pauvreté y a des séries (Sénégal, Dakar, Kolda)."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend import securite
from gestukaay_backend.profil_zone import CHIFFRES_CLES, ProfilZone, profil
from gestukaay_engine.fake import MoteurFactice

client = TestClient(module_app.app)


def lire(code: str) -> ProfilZone:
    r = client.get(f"/v1/zones/{code}")
    assert r.status_code == 200
    return ProfilZone.model_validate(r.json())


def test_region_valeur_periode_source_et_rang():
    p = lire("SN-KD")
    assert p.zone.libelle == "Kolda" and p.zone.niveau == "region"
    [c] = p.chiffres
    assert (c.theme, c.valeur, c.periode) == ("Niveau de vie", 62.5, "2022")
    assert (c.rang, c.sur) == (1, 2) and c.source.libelle  # Kolda devant Dakar parmi les régions publiées
    assert lire("SN-DK").chiffres[0].rang == 2


def test_pays_sans_rang_et_zone_qui_ne_publie_pas():
    assert lire("SN").chiffres[0].rang is None
    thies = lire("SN-TH")
    assert thies.chiffres == [] and [a.libelle for a in thies.absents] == ["Taux de pauvreté"]


def test_zone_inconnue_ou_departement():
    assert client.get("/v1/zones/XX").status_code == 404
    assert client.get("/v1/zones/SN-TH-MBOUR").status_code == 404  # un département ne publie presque rien
    assert securite.groupe("/v1/zones/SN-KD") == "explorer"


class _Projection(MoteurFactice):
    """Kolda reçoit une projection en 2099 : la fiche garde la dernière valeur passée (décision 0035)."""

    def series(self, indicateur, zones, debut=None, fin=None):
        r = super().series(indicateur, zones, debut, fin)
        series = []
        for s in r.series:
            futur = s.points[-1].model_copy(update={"periode": "2099", "libelle": "2099", "nature": "projection"})
            series.append(s.model_copy(update={"points": [*s.points, futur]}))
        return r.model_copy(update={"series": series})


def test_jamais_une_projection_future():
    assert profil(_Projection(), "SN-KD").chiffres[0].periode == "2022"


def test_chiffres_cles_distincts():
    codes = [c.code for c in CHIFFRES_CLES]
    assert len(codes) == len(set(codes)) >= 10
