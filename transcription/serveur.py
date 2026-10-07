# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastapi>=0.115",
#     "uvicorn>=0.30",
#     "python-multipart>=0.0.9",
#     "torch",
#     "transformers<5",
#     "av>=12",
#     "numpy",
# ]
# ///
"""Service de transcription des notes vocales : M-Kiriku (décisions 0026, 0027, issue #28).

Format des API compatibles OpenAI, pour que le moteur l'appelle de la même façon où qu'il tourne
(carte graphique louée, Mac de KBD, PC d'Aziz) :

    POST /v1/audio/transcriptions   champ `file` (OGG/Opus de WhatsApp, WebM/Opus du site, WAV, MP3),
                                    `response_format` json | verbose_json ; réponse {"text", ...}
    GET  /ping                      {"statut": "pret"} une fois le modèle chargé
    GET  /v1/models

Lancer (le modèle est lu dans le cache Hugging Face, ~6 Go la première fois) :

    TRANSCRIPTION_CLE=<jeton choisi> uv run transcription/serveur.py --port 8100
    # puis, côté API Gëstukaay (.env) : TRANSCRIPTION_URL=http://<machine>:8100/v1
    #                                   TRANSCRIPTION_CLE=<le même jeton>

Sans TRANSCRIPTION_CLE, le service n'écoute que sur la machine elle-même (127.0.0.1) et refuse de
s'ouvrir au réseau : sur le wifi d'un hôtel ou d'une salle, n'importe qui pourrait s'en servir.
TRANSCRIPTION_MODELE change de modèle (défaut AIHubSN/M-Kiriku-ASR ; secours AIHubSN/Kiriku-Wolof-ASR).
TRANSCRIPTION_EVEIL_S (défaut 240, 0 = jamais) : après ce délai sans note, une seconde de silence est
transcrite pour garder le modèle chaud. Mesuré le 07/10 sur le Mac (MPS) : après une nuit sans note, la
première a pris 21 s (le moteur abandonne à 5 s), la suivante 1,7 s.
Rien n'est gardé : l'audio est décodé en mémoire puis oublié ; seuls la durée et le temps de calcul
sont journalisés.
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import secrets
import threading
import time

import av
import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, Form, Header, HTTPException, UploadFile
from transformers import pipeline

TAUX = 16_000
DUREE_MAX_S = 61  # EF-11 : 60 s au plus
OCTETS_MAX = 5 * 1024 * 1024
MODELE = os.environ.get("TRANSCRIPTION_MODELE", "AIHubSN/M-Kiriku-ASR")
# Décodage glouton et court (mesuré : 16 s -> 1 s pour une question) ; horodatage au-delà de 30 s
GENERATION = {"max_new_tokens": 128, "num_beams": 1}

EVEIL_S = int(os.environ.get("TRANSCRIPTION_EVEIL_S", "240"))

journal = logging.getLogger("transcription")
app = FastAPI(title="Transcription Gëstukaay", version="1.0")
_asr = None
_verrou = threading.Lock()  # une seule inférence à la fois sur la carte : réveil et vraie note ne se croisent pas
_derniere = time.monotonic()  # dernière inférence (note ou réveil)


def _silence() -> dict:
    """Neuf à chaque appel : le pipeline vide le dictionnaire qu'on lui passe (« raw » retiré)."""
    return {"raw": np.zeros(TAUX, dtype=np.float32), "sampling_rate": TAUX}


def _inferer(entree: dict, **kw) -> dict:
    global _derniere
    with _verrou:
        try:
            return _asr(entree, generate_kwargs=GENERATION, **kw)
        finally:
            _derniere = time.monotonic()


def appareil() -> tuple[str, torch.dtype]:
    if torch.cuda.is_available():
        return "cuda", torch.float16
    if torch.backends.mps.is_available():
        return "mps", torch.float16
    return "cpu", torch.float32  # ~30 s par note : à éviter (0026)


def charger() -> None:
    global _asr
    nom, dtype = appareil()
    journal.warning("chargement de %s sur %s…", MODELE, nom)
    _asr = pipeline("automatic-speech-recognition", model=MODELE, device=nom, torch_dtype=dtype)
    _inferer(_silence())
    journal.warning("prêt.")


def _garder_chaud() -> None:
    """Fil de fond : une seconde de silence quand rien n'est passé depuis EVEIL_S (rien si occupé)."""
    while True:
        time.sleep(max(EVEIL_S / 4, 5))
        if time.monotonic() - _derniere >= EVEIL_S:
            t0 = time.perf_counter()
            _inferer(_silence())
            journal.warning("réveil du modèle en %.2f s", time.perf_counter() - t0)


def decoder(octets: bytes) -> np.ndarray:
    """N'importe quel conteneur audio -> float32 mono 16 kHz, en mémoire."""
    morceaux = []
    with av.open(io.BytesIO(octets)) as conteneur:
        flux = conteneur.streams.audio[0]
        reech = av.AudioResampler(format="flt", layout="mono", rate=TAUX)
        for paquet in conteneur.decode(flux):
            for trame in reech.resample(paquet):
                morceaux.append(trame.to_ndarray().reshape(-1))
        for trame in reech.resample(None):
            morceaux.append(trame.to_ndarray().reshape(-1))
    return np.concatenate(morceaux).astype(np.float32) if morceaux else np.zeros(0, dtype=np.float32)


def autoriser(authorization: str | None) -> None:
    attendu = os.environ.get("TRANSCRIPTION_CLE", "")
    if attendu and not (authorization and secrets.compare_digest(authorization, f"Bearer {attendu}")):
        raise HTTPException(401, "Clé absente ou invalide")


@app.get("/ping")
def ping() -> dict:
    if _asr is None:
        raise HTTPException(503, "chargement")
    return {"statut": "pret", "modele": MODELE}


@app.get("/v1/models")
def modeles() -> dict:
    return {"object": "list", "data": [{"id": "m-kiriku-asr", "object": "model", "owned_by": "AIHubSN"}]}


# Route synchrone : FastAPI la passe dans un fil à part, /ping répond pendant une transcription
@app.post("/v1/audio/transcriptions")
def transcrire(file: UploadFile, model: str = Form("m-kiriku-asr"),
               language: str | None = Form(None), response_format: str = Form("json"),
               authorization: str | None = Header(None)) -> dict:
    autoriser(authorization)
    if _asr is None:
        raise HTTPException(503, "Modèle en cours de chargement")
    octets = file.file.read(OCTETS_MAX + 1)
    if len(octets) > OCTETS_MAX:
        raise HTTPException(413, "Fichier trop gros")
    try:
        audio = decoder(octets)
    except Exception as e:  # noqa: BLE001 — audio illisible : 400, sans le contenu
        raise HTTPException(400, f"Audio illisible ({type(e).__name__})") from None
    finally:
        del octets
    duree = len(audio) / TAUX
    if duree > DUREE_MAX_S:
        raise HTTPException(400, "Note de plus de 60 s")
    t0 = time.perf_counter()
    texte = "" if duree < 0.3 else _inferer({"raw": audio, "sampling_rate": TAUX},
                                            return_timestamps=duree > 30)["text"].strip()
    journal.warning("note de %.1f s transcrite en %.2f s", duree, time.perf_counter() - t0)
    if response_format == "verbose_json":
        return {"text": texte, "duration": round(duree, 2), "language": language}
    return {"text": texte}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Service de transcription M-Kiriku (0026).")
    p.add_argument("--hote", help="0.0.0.0 avec une clé, 127.0.0.1 sans clé (défaut)")
    p.add_argument("--port", type=int, default=8100)
    args = p.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(message)s")
    cle = os.environ.get("TRANSCRIPTION_CLE", "")
    args.hote = args.hote or ("0.0.0.0" if cle else "127.0.0.1")
    if not cle and args.hote not in ("127.0.0.1", "localhost", "::1"):
        p.error("sans TRANSCRIPTION_CLE, le service n'écoute que sur 127.0.0.1 (définir une clé pour l'ouvrir au réseau)")
    charger()
    if EVEIL_S > 0:
        threading.Thread(target=_garder_chaud, name="eveil", daemon=True).start()
    uvicorn.run(app, host=args.hote, port=args.port)
