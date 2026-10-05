"""Transcription des notes vocales (#28, 0026, 0027) : service, repli ADIA, nombres. Réseau simulé."""

import httpx
import pytest
from gestukaay_engine import NonDisponible
from gestukaay_engine.nombres import en_chiffres
from gestukaay_engine.transcription import ADIA_URL, Transcripteur

ENV = {"TRANSCRIPTION_URL": "http://mac.local:8100/v1", "TRANSCRIPTION_CLE": "jeton", "ADIA_API_KEY": "cle-adia"}


@pytest.mark.parametrize("dit, attendu", [
    ("chomage à dakar et à thiès en deux mille vingt quatre", "chomage à dakar et à thiès en 2024"),
    ("des jeunes de quinze à vingt-quatre ans", "des jeunes de 15 à 24 ans"),
    ("quatre-vingt-dix-sept", "97"), ("soixante et onze", "71"), ("mille neuf cent quatre-vingt-dix-neuf", "1999"),
    ("deux millions quatre cent soixante-trois mille six cent soixante-dix-sept", "2463677"),
    ("le taux est de treize virgule deux pour cent", "le taux est de 13,2 pour cent"),
    ("un kilo de riz", "un kilo de riz"), ("cent habitants", "100 habitants"), ("en 2025", "en 2025"),
])
def test_nombres_en_chiffres(dit, attendu):
    assert en_chiffres(dit) == attendu


def transport(service=None, adia=None, appels=None):
    def gerer(r: httpx.Request):
        if appels is not None:
            appels.append((r.url.host, r.headers.get("Authorization")))
        if r.url.host == "mac.local":
            return service(r) if service else httpx.Response(503)
        return adia(r) if adia else httpx.Response(502)
    return httpx.MockTransport(gerer)


def test_service_m_kiriku_puis_nombres_en_chiffres():
    appels = []
    t = Transcripteur(ENV, transport(service=lambda r: httpx.Response(200, json={
        "text": " taux chomage dakar en deux mille vingt quatre ", "duration": 3.42}), appels=appels))
    r = t.transcrire(b"OggS...", "ogg", "auto")
    assert (r.transcription, r.langue, r.duree_s) == ("taux chomage dakar en 2024", "wo", 3.4)
    assert appels == [("mac.local", "Bearer jeton")]  # ADIA jamais appelé


def test_service_tombe_repli_adia():
    appels = []
    t = Transcripteur(ENV, transport(service=lambda r: httpx.Response(503), adia=lambda r: httpx.Response(
        200, json={"text": "ñaata nit ñoo dëkk cees", "usage": {"seconds": 4}}), appels=appels))
    r = t.transcrire(b"OggS...", "ogg", "wo")
    assert (r.transcription, r.langue, r.duree_s) == ("ñaata nit ñoo dëkk cees", "wo", 4.0)
    assert [h for h, _ in appels] == ["mac.local", httpx.URL(ADIA_URL).host]


def test_service_trop_lent_repli_adia():
    def lent(r):
        raise httpx.ReadTimeout("délai dépassé", request=r)
    t = Transcripteur(ENV, transport(service=lent, adia=lambda r: httpx.Response(200, json={"text": "ok"})))
    assert t.transcrire(b"x", "ogg").transcription == "ok"


def test_rien_ne_repond_non_disponible():
    with pytest.raises(NonDisponible):
        Transcripteur(ENV, transport()).transcrire(b"x", "ogg")


def test_rien_de_configure_aucun_appel_reseau():
    appels = []
    with pytest.raises(NonDisponible):
        Transcripteur({}, transport(appels=appels)).transcrire(b"x", "ogg")
    assert appels == []


@pytest.mark.parametrize("dit, attendu", [  # mots et exemples écrits par KBD (0009)
    ("ñaar-fukk ak ñeent", "24"), ("ñaari junni ak ñaar-fukk ak ñeent", "2024"),
    ("ñaari junni ak ñett-fukk", "2030"), ("ñaari junni ak fanweer", "2030"), ("juróom benn fukk", "60"),
    ("junni ak juróom-ñeenti téeméer ak juróom-ñeent-fukk ak juróom-ñeent", "1999"),
    ("fukk ak ñett wirgil ñaar ci téeméer", "13,2 ci téeméer"),
    (("ñaari milyoŋ ak ñeenti téeméer ak juróom-benn-fukk ak ñetti junni ak juróom-benni téeméer ak "
      "juróom-ñaar-fukk ak juróom-ñaar"), "2463677"),
    ("la ko dale fukk ak juróom ba ñaar-fukk ak ñeenti at", "la ko dale 15 ba 24 at"),
    ("Ñaata nit ñoo dëkk Tiés ci atum ñaari junni ak ñaar-fukk ak ñett ?", "Ñaata nit ñoo dëkk Tiés ci atum 2023 ?"),
    # un mot seul qui a un autre sens n'est pas un nombre
    ("benn xale", "benn xale"), ("amul dara", "amul dara"), ("ci fanweer bii", "ci fanweer bii"),
])
def test_nombres_wolof_en_chiffres(dit, attendu):
    assert en_chiffres(dit) == attendu
