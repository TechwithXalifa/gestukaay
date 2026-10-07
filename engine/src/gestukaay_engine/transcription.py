"""Transcription des notes vocales (#28, décisions 0026 et 0027).

  1. le service M-Kiriku (`transcription/serveur.py`), à l'adresse TRANSCRIPTION_URL (format des API
     compatibles OpenAI : POST {url}/audio/transcriptions), 5 s au plus : il tourne sur une carte
     graphique louée, le Mac de KBD ou le PC d'Aziz, et changer de machine = changer l'adresse ;
  2. en repli, ADIA (API payante, ADIA_API_KEY) : la voix part chez un tiers (page Confidentialité) ;
  3. sinon NonDisponible : le canal invite à écrire la question.
Puis les nombres dits en lettres deviennent des chiffres (« deux mille vingt-quatre » -> 2024), et la
langue, si l'appelant ne l'a pas imposée, est déduite du texte (`langue.detecter`).

L'audio ne fait que passer : jamais écrit, jamais journalisé ; les clés non plus (en-têtes seulement).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

import httpx
from gestukaay_contracts.models import TranscriptionResponse

from .interface import NonDisponible
from .langue import detecter
from .nombres import en_chiffres

DELAI_SERVICE_S = 5.0  # attente de la transcription ; au-delà, le service est tombé (choix KBD)
DELAI_ADIA_S = 10.0
DELAI_ENVOI_S = 1.0  # connexion et envoi de la note (≤ 60 s d'Opus, quelques centaines de Ko)
DELAI_CONTROLE_S = 20.0  # relire une note de réponse de 20 s (0029) prend plus qu'une question
ADIA_URL = "https://adia.concree.com/api/v1/asr"
TYPES = {"ogg": "audio/ogg", "webm": "audio/webm", "wav": "audio/wav", "mp3": "audio/mpeg"}
_log = logging.getLogger("gestukaay.transcription")


class Transcripteur:
    def __init__(self, env: Mapping[str, str] = os.environ, transport: httpx.BaseTransport | None = None):
        self._env = env
        self._transport = transport

    def transcrire(self, audio: bytes, format_audio: str, langue: str = "auto") -> TranscriptionResponse:
        fichier = (f"note.{format_audio}", audio, TYPES.get(format_audio, "application/octet-stream"))
        for nom, essai in (("service", self._service), ("ADIA", self._adia)):
            try:
                texte, duree = essai(fichier, langue)
            except (httpx.HTTPError, KeyError, ValueError, _Absent) as e:
                _log.warning("transcription : %s indisponible (%s)", nom, type(e).__name__)
                continue
            texte = en_chiffres(texte.strip())
            return TranscriptionResponse(transcription=texte, duree_s=round(duree, 1),
                                         langue=langue if langue in ("fr", "wo") else detecter(texte))
        raise NonDisponible("transcription : service et repli indisponibles")

    def relire(self, audio: bytes, format_audio: str = "wav") -> str | None:
        """Contrôle d'une note de synthèse (0029) : le service seul, jamais ADIA (payant) ; None si le
        service ne répond pas (la note n'est alors pas contrôlée)."""
        fichier = (f"note.{format_audio}", audio, TYPES.get(format_audio, "application/octet-stream"))
        try:
            return self._service(fichier, "wo", DELAI_CONTROLE_S)[0].strip()
        except (httpx.HTTPError, KeyError, ValueError, _Absent) as e:
            _log.warning("contrôle de la voix : service de transcription indisponible (%s)", type(e).__name__)
            return None

    def _client(self, delai: float, **kw) -> httpx.Client:
        """httpx applique un délai à chaque étape, pas au total : connexion et envoi ont le leur (1 s),
        l'attente de la réponse a `delai`. Au pire 1 + 1 + 5 = 7 s avant de passer au repli."""
        temps = httpx.Timeout(delai, connect=DELAI_ENVOI_S, write=DELAI_ENVOI_S, pool=DELAI_ENVOI_S)
        return httpx.Client(timeout=temps, transport=self._transport, **kw)

    def _service(self, fichier: tuple, langue: str, delai: float = DELAI_SERVICE_S) -> tuple[str, float]:
        url = self._env.get("TRANSCRIPTION_URL", "").rstrip("/")
        if not url:
            raise _Absent("TRANSCRIPTION_URL")
        cle = self._env.get("TRANSCRIPTION_CLE", "")
        donnees = {"model": "m-kiriku-asr", "response_format": "verbose_json"}
        if langue in ("fr", "wo"):
            donnees["language"] = langue
        with self._client(delai, headers={"Authorization": f"Bearer {cle}"} if cle else {}) as h:
            r = h.post(f"{url}/audio/transcriptions", files={"file": fichier}, data=donnees)
            r.raise_for_status()
            j = r.json()
        return j["text"], float(j.get("duration") or 0)

    def _adia(self, fichier: tuple, langue: str) -> tuple[str, float]:
        cle = self._env.get("ADIA_API_KEY", "")
        if not cle:
            raise _Absent("ADIA_API_KEY")
        with self._client(DELAI_ADIA_S, headers={"Authorization": f"Bearer {cle}"}) as h:
            r = h.post(ADIA_URL, files={"audio": fichier}, data={"language": "wolof"})
            r.raise_for_status()
            j = r.json()
        return j["text"], float((j.get("usage") or {}).get("seconds") or 0)


class _Absent(Exception):
    """Service non configuré : on passe au suivant, sans appel réseau."""
