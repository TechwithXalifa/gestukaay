"""Voix de réponse : le texte wolof (`parole.py`) devient une note OGG/Opus (#29, #30, décision 0029).

  1. le service Oolel (`synthese/serveur.py`), à l'adresse SYNTHESE_URL (format des API compatibles
     OpenAI : POST {url}/audio/speech), qui tourne sur une carte graphique louée ou la machine de
     l'équipe. Oolel change « : » en virgule : on découpe donc le texte et on insère nous-mêmes les
     silences (0,6 s après « : », 0,3 s entre les phrases ; choix de KBD à l'écoute) ;
  2. contrôle : M-Kiriku relit la note (service de transcription seul, jamais ADIA) ; on compare les
     lettres hors nombres (M-Kiriku relit mal les grands nombres qu'Oolel dit bien). Seuil calibré sur
     les notes écoutées par KBD : ses 6 notes jugées bonnes passent (0,86 à 0,99), les 4 ratées qu'il
     avait signalées sont rejetées. Note rejetée : un 2e tirage, puis ADIA ;
  3. en repli, ADIA (API payante, ADIA_API_KEY) ; sinon None : le texte part seul.
Opus 20 kbps : 20 s = 50 Ko. Une note plus longue (choix KBD : elle part quand même) baisse son débit
pour rester sous 60 Ko. Le texte et l'audio ne sont ni écrits sur disque ni journalisés.
"""

from __future__ import annotations

import difflib
import io
import logging
import os
import re
import unicodedata
import wave
from collections.abc import Mapping

import httpx

from .interface import NoteVocale
from .transcription import Transcripteur

DELAI_SERVICE_S = 30.0  # une phrase : le calcul dure à peu près sa durée sur un Mac
DELAI_ADIA_S = 30.0
ADIA_TTS_URL = "https://adia.concree.com/api/v1/tts"
ADIA_VOIX = "marietou"
PAUSE_DEUX_POINTS_S, PAUSE_PHRASE_S = 0.6, 0.3
SEUIL_RESSEMBLANCE = 0.80
LONGUEUR_ADMISE = (0.75, 1.4)  # longueur relue / attendue : une boucle allonge, un mot sauté raccourcit
OCTETS_MAX = 60_000  # #30
DEBIT_BPS, DEBIT_MIN_BPS = 20_000, 8_000
_log = logging.getLogger("gestukaay.synthese")


def morceaux(texte: str) -> list[tuple[str, float]]:
    """(phrase, silence après) : on coupe entre les phrases et après « : » (Oolel ne fait pas la pause)."""
    out = []
    for phrase in re.split(r"(?<=[.?!])\s+(?=[^»\s])", texte.strip()):  # « … ? » reste entier
        parties = [p.strip() for p in phrase.split(":")]
        for k, p in enumerate(parties):
            if not p:
                continue
            dernier = k == len(parties) - 1
            out.append((p if dernier else f"{p}.", PAUSE_PHRASE_S if dernier else PAUSE_DEUX_POINTS_S))
    return out


# --- Contrôle -----------------------------------------------------------------

_MOTS_NOMBRES = {  # sans accent ; « ci » et « ak » aussi (ci téeméer, liaisons des nombres)
    "tus", "dara", "benn", "ben", "naar", "nett", "neent", "juroom", "fukk", "fanweer", "teemeer", "junni",
    "milyong", "milyaar", "wirgil", "ak", "ci", "un", "une", "deux", "trois", "quatre", "cinq", "six", "sept",
    "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "vingt", "trente",
    "quarante", "cinquante", "soixante", "cent", "cents", "mille", "million", "millions", "virgule", "et",
}


def sans_nombres(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte.lower().replace("ŋ", "ng")).encode("ascii", "ignore").decode()
    garde = []
    for m in re.findall(r"[a-z]+", t):
        base = m[:-1] if m.endswith(("i", "y")) and m[:-1] in _MOTS_NOMBRES else m
        if base not in _MOTS_NOMBRES and not base.startswith(("milyo", "milio", "milya")):
            garde.append(m)
    return " ".join(garde)


def conforme(attendu: str, relu: str) -> bool:
    a, b = sans_nombres(attendu), sans_nombres(relu)
    if not a:
        return True
    ressemblance = difflib.SequenceMatcher(None, a, b).ratio()
    longueur = len(b) / len(a)
    return ressemblance >= SEUIL_RESSEMBLANCE and LONGUEUR_ADMISE[0] <= longueur <= LONGUEUR_ADMISE[1]


# --- Audio --------------------------------------------------------------------


def lire_wav(octets: bytes) -> tuple[bytes, int]:
    """WAV PCM 16 bits mono -> (échantillons, fréquence)."""
    with wave.open(io.BytesIO(octets)) as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise ValueError("WAV attendu : PCM 16 bits mono")
        return w.readframes(w.getnframes()), w.getframerate()


def ecrire_wav(pcm: bytes, taux: int) -> bytes:
    sortie = io.BytesIO()
    with wave.open(sortie, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taux)
        w.writeframes(pcm)
    return sortie.getvalue()


def en_opus(pcm: bytes, taux: int, debit: int) -> bytes:
    # PyAV importé ici seulement : le moteur doit se charger partout, même là où PyAV est bloqué (poste
    # Windows de SAN, revue #136) ; il n'est requis que là où une note est vraiment fabriquée
    import av

    sortie = io.BytesIO()
    with av.open(sortie, "w", format="ogg") as c:
        flux = c.add_stream("libopus", rate=24000, layout="mono")
        flux.bit_rate = debit
        trame = av.AudioFrame(format="s16", layout="mono", samples=len(pcm) // 2)
        trame.sample_rate = taux
        trame.planes[0].update(pcm)
        for paquet in [*flux.encode(trame), *flux.encode(None)]:
            c.mux(paquet)
    return sortie.getvalue()


def note_opus(pcm: bytes, taux: int) -> tuple[bytes, float]:
    """OGG/Opus de 60 Ko au plus (#30) : 20 kbps, moins pour une note de plus de 20 s (choix KBD)."""
    duree = len(pcm) / 2 / taux
    debit = min(DEBIT_BPS, int(OCTETS_MAX * 8 * 0.9 / max(duree, 0.1)))
    while True:
        opus = en_opus(pcm, taux, max(debit, DEBIT_MIN_BPS))
        if len(opus) <= OCTETS_MAX or debit <= DEBIT_MIN_BPS:
            return opus, round(duree, 1)
        debit -= 2_000


# --- Synthèse -----------------------------------------------------------------


class Synthetiseur:
    def __init__(self, env: Mapping[str, str] = os.environ, transport: httpx.BaseTransport | None = None,
                 transcripteur: Transcripteur | None = None):
        self._env = env
        self._transport = transport
        self._transcripteur = transcripteur or Transcripteur(env, transport)

    def parler(self, texte: str) -> NoteVocale | None:
        if not texte.strip():
            return None
        for tirage in (1, 2):
            try:
                pcm, taux = self._oolel(texte, tirage)
            except (httpx.HTTPError, ValueError, _Absent) as e:
                _log.warning("voix : Oolel indisponible (%s)", type(e).__name__)
                break
            relu = self._transcripteur.relire(ecrire_wav(pcm, taux))
            if relu is None or conforme(texte, relu):  # service de contrôle absent : note acceptée
                return NoteVocale(*note_opus(pcm, taux), voix="oolel")
            _log.warning("voix : note rejetée par le contrôle (tirage %d)", tirage)
        try:
            pcm, taux = self._adia(texte)
        except (httpx.HTTPError, ValueError, _Absent) as e:
            _log.warning("voix : ADIA indisponible (%s) : texte seul", type(e).__name__)
            return None
        return NoteVocale(*note_opus(pcm, taux), voix="adia")

    def _client(self, delai: float, cle: str) -> httpx.Client:
        temps = httpx.Timeout(delai, connect=2.0)
        return httpx.Client(timeout=temps, transport=self._transport,
                            headers={"Authorization": f"Bearer {cle}"} if cle else {})

    def _oolel(self, texte: str, tirage: int) -> tuple[bytes, int]:
        url = self._env.get("SYNTHESE_URL", "").rstrip("/")
        if not url:
            raise _Absent("SYNTHESE_URL")
        pcm, taux = b"", None
        with self._client(DELAI_SERVICE_S, self._env.get("SYNTHESE_CLE", "")) as h:
            for phrase, silence in morceaux(texte):
                r = h.post(f"{url}/audio/speech", json={"model": "oolel-voices", "input": phrase,
                                                        "response_format": "wav", "seed": tirage})
                r.raise_for_status()
                bout, t = lire_wav(r.content)
                if taux not in (None, t):
                    raise ValueError("fréquences différentes entre les phrases")
                taux = t
                pcm += bout + b"\x00\x00" * int(silence * t)
        if taux is None:
            raise ValueError("texte vide")
        return pcm, taux

    def _adia(self, texte: str) -> tuple[bytes, int]:
        cle = self._env.get("ADIA_API_KEY", "")
        if not cle:
            raise _Absent("ADIA_API_KEY")
        with self._client(DELAI_ADIA_S, cle) as h:
            r = h.post(ADIA_TTS_URL, json={"text": texte, "voice": ADIA_VOIX})
            r.raise_for_status()
            _log.warning("voix : repli ADIA (%s FCFA)", r.headers.get("X-Adia-Cost-Fcfa", "?"))
            return lire_wav(r.content)


class _Absent(Exception):
    """Service non configuré : on passe au suivant, sans appel réseau."""
