"""Transcription des notes vocales (#28, 0026, 0027) : service, repli ADIA, nombres. Réseau simulé."""

import httpx
import pytest
from gestukaay_engine import NonDisponible
from gestukaay_engine.langue import detecter
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
        "text": " Ñaata nit ñoo dëkk Tiés ci atum ñaari junni ak ñaar-fukk ak ñett ", "duration": 3.42}),
        appels=appels))
    r = t.transcrire(b"OggS...", "ogg", "auto")
    assert (r.transcription, r.langue, r.duree_s) == ("Ñaata nit ñoo dëkk Tiés ci atum 2023", "wo", 3.4)
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
    # sauf devant « wirgil » : « tus wirgil juróom ci téeméer » = 0,5 % (KBD, fiche 2)
    ("tus wirgil juróom ci téeméer", "0,5 ci téeméer"), ("fanweer wirgil ñaar", "30,2"),
    # le suffixe -i sur fukk, fanweer, téeméer, junni (KBD, fiche 2)
    ("fukki junni", "10000"), ("fanweeri junni", "30000"), ("téeméeri junni", "100000"),
    ("juróom-ñeent-fukki junni", "90000"), ("fukk ak ñaari junniy ton", "12000 ton"),
])
def test_nombres_wolof_en_chiffres(dit, attendu):
    assert en_chiffres(dit) == attendu


@pytest.mark.parametrize("dit, attendu", [  # questions d'évolution : deux années, jamais un seul nombre (Aziz, #125)
    ("Le taux de pauvreté a-t-il baissé entre deux mille onze et deux mille vingt-deux ?",
     "Le taux de pauvreté a-t-il baissé entre 2011 et 2022 ?"),
    ("Chômage en deux mille vingt-quatre et deux mille vingt-cinq", "Chômage en 2024 et 2025"),
    ("diggante ñaari junni ak fukk ak benn ak ñaari junni ak ñaar-fukk ak ñaar", "diggante 2011 ak 2022"),
    ("ñaari junni ak juróom ak junni ak juróom-ñeenti téeméer ak juróom-ñeent-fukk ak juróom-ñeent",
     "2005 ak 1999"),
    ("cent un et deux cents", "101 et 200"), ("trente et une", "31"),
])
def test_deux_nombres_relies_restent_deux(dit, attendu):
    assert en_chiffres(dit) == attendu


@pytest.mark.parametrize("texte, langue", [  # questions du jeu de test et notes vocales transcrites
    ("Combien d'habitants à Thiès ?", "fr"),
    ("Quel est le taux de chômage des jeunes de 15 à 24 ans au Sénégal en 2025 ?", "fr"),
    ("Et pour Kaolack ?", "fr"), ("taux de pauvreté au sénégal", "fr"),
    ("ñaata nit ñoo dëkk thiès", "wo"), ("Ñi amul ligéey ci Senegaal ?", "wo"),
    ("Ñata xale moins de 5 ans nioy de senegal (sur 1000) ?", "wo"),  # interrogatif wolof : tranche
    ("Ndax prix thieb detail bi yok na entre mars 2025 ak mars 2026 ?", "wo"),
    ("Limu askanu Ndakaaru ak Kaolack", "wo"), ("Kaolack nak?", "wo"),
])
def test_langue_detectee(texte, langue):
    assert detecter(texte) == langue


def test_langue_deduite_du_texte_si_non_imposee():
    """Le site envoie « auto » : une question dite en français repart en français (Aziz, #125)."""
    rep = lambda r: httpx.Response(200, json={"text": "quel est le taux de chômage à dakar", "duration": 2})
    assert Transcripteur(ENV, transport(service=rep)).transcrire(b"x", "webm").langue == "fr"
    assert Transcripteur(ENV, transport(service=rep)).transcrire(b"x", "webm", "wo").langue == "wo"  # imposée
