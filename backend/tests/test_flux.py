"""Alertes de nouvelle publication : flux Atom par indicateur et par zone (faux moteur : taux de pauvreté)."""

import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend import securite

client = TestClient(module_app.app)
ATOM = "{http://www.w3.org/2005/Atom}"
PAUVRETE = "jcvcajc.taux-de-pauvrete"


def test_flux_atom_valide_avec_les_valeurs_et_la_source():
    r = client.get(f"/v1/indicators/{PAUVRETE}/flux.atom", params={"zone": "SN-KD"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/atom+xml")
    flux = ET.fromstring(r.content)  # XML bien formé
    assert flux.find(f"{ATOM}title").text == "Taux de pauvreté · Kolda · Gëstukaay"
    entrees = flux.findall(f"{ATOM}entry")
    titres = [e.find(f"{ATOM}title").text for e in entrees]
    assert titres[0] == "Taux de pauvreté · Kolda · 2022 : 62,5 %"  # la plus récente d'abord
    assert len(entrees) == 3 and all("Source : ANSD" in e.find(f"{ATOM}summary").text for e in entrees)
    lien = entrees[0].find(f"{ATOM}link").get("href")
    assert lien.endswith("/explorer?indicateur=jcvcajc.taux-de-pauvrete&zones=SN%2CSN-KD")
    # Une valeur révisée change d'identifiant : le lecteur de flux la signale comme nouvelle
    assert entrees[0].find(f"{ATOM}id").text.endswith(":SN-KD:2022:62.5")


def test_zone_sans_valeur_et_indicateur_inconnu():
    vide = ET.fromstring(client.get(f"/v1/indicators/{PAUVRETE}/flux.atom", params={"zone": "SN-TH"}).content)
    assert vide.findall(f"{ATOM}entry") == []  # flux vide mais valide
    assert client.get("/v1/indicators/inconnu/flux.atom").status_code == 404
    assert securite.groupe(f"/v1/indicators/{PAUVRETE}/flux.atom") == "explorer"
