import logging

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_contracts.models import SituateResponse

client = TestClient(module_app.app)
SAISIE = {"region": "SN-KD", "taille_menage": 7, "depenses_mensuelles": "100k_200k"}


def test_resultat_conforme_et_source():
    r = client.post("/v1/situate", json=SAISIE)
    assert r.status_code == 200
    rep = SituateResponse.model_validate(r.json())
    for v in [rep.moyenne_region, rep.moyenne_pays, *rep.contexte]:
        assert v.source.libelle  # aucune valeur sans source


def test_rien_n_est_conserve(caplog):
    """EF-40, US-21 : aucune donnée saisie en mémoire ni dans les journaux."""
    avant = dict(module_app._reponses)
    with caplog.at_level(logging.DEBUG):
        client.post("/v1/situate", json=SAISIE | {"taille_menage": 13})
    assert module_app._reponses == avant
    assert "13" not in caplog.text and "100k_200k" not in caplog.text


def test_saisie_invalide_refusee():
    for mauvaise in [{**SAISIE, "taille_menage": 0}, {**SAISIE, "depenses_mensuelles": "beaucoup"}, {"region": "SN-KD"}]:
        assert client.post("/v1/situate", json=mauvaise).status_code == 422
