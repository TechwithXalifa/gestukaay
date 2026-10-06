# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastapi>=0.115",
#     "uvicorn>=0.30",
#     "torch",
#     "torchaudio",
#     "transformers==4.46.3",
#     "diffusers==0.29.0",
#     "conformer==0.3.2",
#     "librosa",
#     "s3tokenizer",
#     "safetensors",
#     "huggingface_hub",
#     "omegaconf",
#     "einops",
#     "scipy",
#     "numpy",
# ]
# ///
"""Service de voix de réponse : Oolel-Voices (Soynade Research), décision 0029, issue #29.

Oolel est utilisé TEL QUEL (licence AGPL-3.0 : https://huggingface.co/soynade-research/Oolel-Voices) ;
ce service ne fait que le charger et lui passer une phrase. Le découpage du texte, les silences, le
contrôle et l'encodage Opus sont faits par le moteur (`engine/…/synthese.py`).

Format des API compatibles OpenAI, pour que le moteur l'appelle de la même façon où qu'il tourne :

    POST /v1/audio/speech   JSON {"input": "<une phrase>", "response_format": "wav", "seed": 1}
                            -> WAV PCM 16 bits mono ; « seed » change le tirage (2e essai)
    GET  /ping              {"statut": "pret"} une fois le modèle chargé
    GET  /v1/models

Lancer (modèle lu dans le cache Hugging Face, ~8,5 Go la première fois) :

    SYNTHESE_CLE=<jeton choisi> uv run synthese/serveur.py --port 8200
    # puis, côté API Gëstukaay (.env) : SYNTHESE_URL=http://<machine>:8200/v1
    #                                   SYNTHESE_CLE=<le même jeton>

SYNTHESE_VOIX : enregistrement de la voix de référence (WAV, 10 à 20 s, accord écrit de la personne) ;
par défaut, la voix de la démo d'Oolel. Sans SYNTHESE_CLE, le service n'écoute que sur 127.0.0.1.
Rien n'est gardé : seuls la longueur du texte et le temps de calcul sont journalisés.
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import secrets
import threading
import time
import wave

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Response
from huggingface_hub import hf_hub_download, snapshot_download
from pydantic import BaseModel, Field
from transformers import AutoModel

MODELE = "soynade-research/Oolel-Voices"
REGLAGE = {"cfg_weight": 0.5, "exaggeration": 0.2, "temperature": 0.3}  # réglage prudent (0029)
CARACTERES_MAX = 600

journal = logging.getLogger("synthese")
app = FastAPI(title="Voix Gëstukaay", version="1.0")
_oolel = None
_voix = ""
_verrou = threading.Lock()  # une seule synthèse à la fois sur la carte graphique


class Demande(BaseModel):
    input: str = Field(min_length=1, max_length=CARACTERES_MAX)
    model: str = "oolel-voices"
    response_format: str = "wav"
    seed: int = 1


def appareil() -> str:
    if torch.cuda.is_available():
        return "cuda"
    return "mps" if torch.backends.mps.is_available() else "cpu"


def charger() -> None:
    global _oolel, _voix
    _voix = os.environ.get("SYNTHESE_VOIX") or hf_hub_download(
        "soynade-research/Oolel-Voices-Demo", "8_1_c.wav", repo_type="space")
    nom = appareil()
    journal.warning("chargement d'Oolel sur %s…", nom)
    _oolel = AutoModel.from_pretrained(snapshot_download(MODELE), trust_remote_code=True, device_map=nom)
    _oolel.generate("Salamaleekum", audio_prompt_path=_voix)  # chauffe
    journal.warning("prêt.")


def autoriser(authorization: str | None) -> None:
    attendu = os.environ.get("SYNTHESE_CLE", "")
    if attendu and not (authorization and secrets.compare_digest(authorization, f"Bearer {attendu}")):
        raise HTTPException(401, "Clé absente ou invalide")


@app.get("/ping")
def ping() -> dict:
    if _oolel is None:
        raise HTTPException(503, "chargement")
    return {"statut": "pret", "modele": MODELE}


@app.get("/v1/models")
def modeles() -> dict:
    return {"object": "list", "data": [{"id": "oolel-voices", "object": "model", "owned_by": "soynade-research"}]}


# Route synchrone : FastAPI la passe dans un fil à part, /ping répond pendant une synthèse
@app.post("/v1/audio/speech")
def parler(d: Demande, authorization: str | None = Header(None)) -> Response:
    autoriser(authorization)
    if _oolel is None:
        raise HTTPException(503, "Modèle en cours de chargement")
    if d.response_format != "wav":
        raise HTTPException(400, "response_format : wav seulement (l'Opus est fait par le moteur)")
    t0 = time.perf_counter()
    with _verrou:
        torch.manual_seed(d.seed)
        onde = _oolel.generate(d.input, audio_prompt_path=_voix, **REGLAGE).squeeze().float().cpu().numpy()
    pcm = (np.clip(onde, -1, 1) * 32767).astype("<i2").tobytes()
    journal.warning("%d caractères -> %.1f s en %.1f s", len(d.input), len(pcm) / 2 / _oolel.sr,
                    time.perf_counter() - t0)
    sortie = io.BytesIO()
    with wave.open(sortie, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_oolel.sr)
        w.writeframes(pcm)
    return Response(sortie.getvalue(), media_type="audio/wav")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Service de voix Oolel (0029).")
    p.add_argument("--hote", help="0.0.0.0 avec une clé, 127.0.0.1 sans clé (défaut)")
    p.add_argument("--port", type=int, default=8200)
    args = p.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(message)s")
    cle = os.environ.get("SYNTHESE_CLE", "")
    args.hote = args.hote or ("0.0.0.0" if cle else "127.0.0.1")
    if not cle and args.hote not in ("127.0.0.1", "localhost", "::1"):
        p.error("sans SYNTHESE_CLE, le service n'écoute que sur 127.0.0.1 (définir une clé pour l'ouvrir au réseau)")
    charger()
    uvicorn.run(app, host=args.hote, port=args.port)
