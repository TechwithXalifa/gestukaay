"""Voix de réponse (#29, #30, décision 0029) : service Oolel, contrôle M-Kiriku, repli ADIA, Opus.
Réseau simulé : aucun modèle, aucun appel réel."""

import io
import json
import math
import struct

import httpx
import pytest
from gestukaay_engine.synthese import (
    ADIA_TTS_URL,
    OCTETS_MAX,
    PAUSE_DEUX_POINTS_S,
    PAUSE_PHRASE_S,
    Synthetiseur,
    conforme,
    ecrire_wav,
    morceaux,
    note_opus,
)

av = pytest.importorskip("av")  # tests d'encodage seulement : sautés là où PyAV est bloqué

TAUX = 24000


def voix(secondes: float, taux: int = TAUX) -> bytes:
    """Signal qui ressemble à de la parole (sinus modulé) : PCM 16 bits mono."""
    n = int(secondes * taux)
    return b"".join(struct.pack("<h", int(9000 * math.sin(i / 6) * (0.4 + 0.6 * abs(math.sin(i / 1800)))))
                    for i in range(n))


def duree_ogg(opus: bytes) -> float:
    with av.open(io.BytesIO(opus)) as c:
        return c.duration / av.time_base


# --- Découpe et contrôle ------------------------------------------------------


def test_decoupe_aux_deux_points_et_entre_les_phrases():
    """Oolel change « : » en virgule : on découpe et on met nos silences (choix de KBD à l'écoute)."""
    t = "Xéyna dégguma la bu baax. Mën nga jéem laaj bii, niki : « Ñaata nit ñoo dëkk Cees ? »"
    assert morceaux(t) == [("Xéyna dégguma la bu baax.", PAUSE_PHRASE_S),
                           ("Mën nga jéem laaj bii, niki.", PAUSE_DEUX_POINTS_S),
                           ("« Ñaata nit ñoo dëkk Cees ? »", PAUSE_PHRASE_S)]


BONNE = ("Tolluwaayu ñàkk bi ci Senegaal mi ngi tollu ci fanweer ak juróom-ñaar wirgil juróom ci téeméer ci "
         "atum deux mille vingt-deux.")


@pytest.mark.parametrize("attendu, relu, ok", [
    # notes jugées bonnes par KBD : M-Kiriku relit mal les nombres, peu importe
    (BONNE, "tolluwaayu ñàkk bi ci senegaal mi ngi toll ci 32 juróom ci téemeer ci atum 2022", True),
    (("Am na ñaari milyoŋ ak ñeenti téeméer ak juróom-benn-fukk ak ñetti junni nit ci diiwaanu Cees ci atum "
      "deux mille vingt-trois."),
     ("am na ñaari million ak ñeenti téeméer ak juróom benn fukk ak ñeenti junni nit ci diwaanu thiès ci "
      "atum 2023"), True),
    # notes ratées signalées par KBD : boucle, premier mot sauté
    ("Ñata nitt nio nek kaso senegal ?", "kaso senegaal nek kaso senegaal mete na ñu nekk kaso senegaal", False),
    ("Proportion xale yi am vaccins yeup tamba", "xale yi am vaccin yëpp tamba", False),
])
def test_controle_calibre_sur_les_notes_ecoutees_par_kbd(attendu, relu, ok):
    assert conforme(attendu, relu) is ok


# --- Opus (#30) ---------------------------------------------------------------


@pytest.mark.parametrize("secondes", [3, 20, 32])
def test_note_opus_60_ko_au_plus(secondes):
    """#30 : 20 s tiennent sous 60 Ko à 20 kbps ; plus longue (choix KBD), le débit baisse."""
    opus, duree = note_opus(voix(secondes), TAUX)
    assert len(opus) <= OCTETS_MAX and opus[:4] == b"OggS"
    assert duree == secondes and abs(duree_ogg(opus) - secondes) < 0.1


# --- Chaîne complète, réseau simulé ---------------------------------------------

ENV = {"SYNTHESE_URL": "http://gpu.local:8200/v1", "SYNTHESE_CLE": "jeton-voix",
       "TRANSCRIPTION_URL": "http://mac.local:8100/v1", "ADIA_API_KEY": "cle-adia"}
TEXTE = "Lim bii amul ci xibaari A-EN-ES-DE yi ñu yor. Li ko wóoral : A-EN-ES-DE."


def reseau(appels, oolel=None, relu="lim bii amul ci xibaari a en es de yi ñu yor li ko wóoral a en es de",
           adia=None, controle=200):
    def gerer(r: httpx.Request):
        appels.append((r.url.host, r.url.path, r.headers.get("Authorization")))
        if r.url.host == "gpu.local":
            if oolel is not None:
                return oolel(r)
            phrase = json.loads(r.content)["input"]
            return httpx.Response(200, content=ecrire_wav(voix(0.05 * len(phrase)), TAUX))
        if r.url.host == "mac.local":
            return httpx.Response(controle, json={"text": relu, "duration": 3})
        if adia is not None:
            return adia(r)
        return httpx.Response(200, content=ecrire_wav(voix(2.0), 22050))
    return httpx.MockTransport(gerer)


def test_oolel_controle_accepte():
    appels = []
    note = Synthetiseur(ENV, reseau(appels)).parler(TEXTE)
    assert note.voix == "oolel" and note.opus[:4] == b"OggS"
    phrases = [a for a in appels if a[0] == "gpu.local"]
    assert len(phrases) == 3 and all(a == ("gpu.local", "/v1/audio/speech", "Bearer jeton-voix") for a in phrases)
    assert [a[0] for a in appels].count("mac.local") == 1  # un seul contrôle
    attendu = sum(0.05 * len(p) for p, _ in morceaux(TEXTE)) + PAUSE_PHRASE_S * 2 + PAUSE_DEUX_POINTS_S
    assert abs(note.duree_s - attendu) < 0.15  # les silences sont bien insérés


def test_note_rejetee_deux_fois_repli_adia():
    appels = []
    note = Synthetiseur(ENV, reseau(appels, relu="kaso senegaal kaso senegaal")).parler(TEXTE)
    assert note.voix == "adia"
    assert [a[0] for a in appels].count("mac.local") == 2  # deux tirages contrôlés
    assert appels[-1][0] == httpx.URL(ADIA_TTS_URL).host and appels[-1][2] == "Bearer cle-adia"


def test_oolel_tombe_repli_adia():
    appels = []
    note = Synthetiseur(ENV, reseau(appels, oolel=lambda r: httpx.Response(503))).parler(TEXTE)
    assert note.voix == "adia" and "mac.local" not in [a[0] for a in appels]


def test_controle_indisponible_note_acceptee_sans_payer_adia():
    """Le contrôle passe par le service de transcription seul : jamais par ADIA (payant)."""
    appels = []
    note = Synthetiseur(ENV, reseau(appels, controle=503)).parler(TEXTE)
    assert note.voix == "oolel" and httpx.URL(ADIA_TTS_URL).host not in [a[0] for a in appels]


def test_rien_ne_repond_texte_seul():
    appels = []
    note = Synthetiseur(ENV, reseau(appels, oolel=lambda r: httpx.Response(503),
                                    adia=lambda r: httpx.Response(502))).parler(TEXTE)
    assert note is None


def test_rien_de_configure_aucun_appel_reseau():
    appels = []
    assert Synthetiseur({}, reseau(appels)).parler(TEXTE) is None and appels == []


def test_le_moteur_se_charge_sans_pyav():
    # revue #136 : sur le Windows de SAN, PyAV est bloqué ; le moteur doit quand même se charger
    import subprocess
    import sys
    code = ("import sys; import gestukaay_engine.moteur, gestukaay_engine.synthese; "
            "print('av' in sys.modules)")
    sortie = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert sortie.stdout.strip() == "False"



def test_la_note_porte_le_texte_parle():
    # revue #136 : le site affiche sous le lecteur ce que la note dit (cahier 7.5 et 9.7)
    from gestukaay_contracts.models import AskRequest
    from gestukaay_engine.interface import NoteVocale
    from test_moteur import MOTEUR

    class Faux:
        def parler(self, texte):
            return NoteVocale(b"OggS", 3.0, "oolel")

    avant, MOTEUR.synthetiseur = MOTEUR.synthetiseur, Faux()
    try:
        note = MOTEUR.parler(MOTEUR.repondre(AskRequest(question="Combien d'habitants à Thiès ?")))
    finally:
        MOTEUR.synthetiseur = avant  # MOTEUR est partagé avec les autres fichiers de tests
    assert note.voix == "oolel" and "Cees" in note.texte
