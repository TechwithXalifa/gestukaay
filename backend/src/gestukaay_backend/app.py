"""API Gëstukaay — squelette de bout en bout (tâche 7.1).

    uv run uvicorn gestukaay_backend.app:app --reload --port 8000

Le backend ne transforme pas la réponse du moteur : il la complète
(`latence_ms`), la stocke et la renvoie telle quelle (contrat-v1 §1).
Stockage en mémoire pour le squelette ; la persistance viendra ensuite.
"""

from __future__ import annotations

import os
import time
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from gestukaay_contracts.models import (
    AskRequest,
    AskResponse,
    ConfirmRequest,
    FeedbackRequest,
    Problem,
    ReponseApprochee,
    ReponseExacte,
)
from gestukaay_engine import charger_moteur

from .exports import vers_csv, vers_pdf

app = FastAPI(title="Gëstukaay", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("GESTUKAAY_URL_PUBLIQUE", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

moteur = charger_moteur()
_reponses: dict[str, AskResponse] = {}


class ErreurApi(Exception):
    def __init__(self, status: int, title: str, detail: str | None = None):
        self.probleme = Problem(title=title, status=status, detail=detail)


@app.exception_handler(ErreurApi)
async def _probleme(_: Request, exc: ErreurApi) -> JSONResponse:
    # RFC 9457 [10.6]
    return JSONResponse(
        exc.probleme.model_dump(),
        status_code=exc.probleme.status,
        media_type="application/problem+json",
    )


URL_PUBLIQUE = os.environ.get("GESTUKAAY_URL_PUBLIQUE", "http://localhost:3000").split(",")[0]


def _conserver(rep: AskResponse, debut: float) -> AskResponse:
    # Les URL relèvent du backend (interface.py) : adresse stable du site [EF-29]
    rep.reponse.url = f"{URL_PUBLIQUE.rstrip('/')}/r/{rep.reponse.id}"
    rep.reponse.latence_ms = round((time.perf_counter() - debut) * 1000)
    _reponses[rep.reponse.id] = rep
    return rep


@app.get("/health")
def sante() -> dict:
    return {"statut": "ok", "version_socle": moteur.version_socle()}


@app.post("/v1/ask", response_model=AskResponse)
def demander(req: AskRequest) -> AskResponse:
    debut = time.perf_counter()
    return _conserver(moteur.repondre(req), debut)


@app.post("/v1/ask/{rid}/confirm", response_model=AskResponse)
def confirmer(rid: str, req: ConfirmRequest) -> AskResponse:
    debut = time.perf_counter()
    stockee = _reponses.get(rid)
    if stockee is None:
        raise ErreurApi(404, "Réponse introuvable")
    rep = stockee.reponse
    if not isinstance(rep, ReponseApprochee):
        raise ErreurApi(409, "Cette réponse n'attend pas de confirmation")
    choix = next((c for c in rep.choix if c.id == req.choix_id), None)
    if choix is None:
        raise ErreurApi(422, "Choix inconnu", f"choix_id={req.choix_id!r}")
    return _conserver(moteur.executer(choix.requete, rep.question, rep.langue), debut)


@app.get("/v1/answers/{rid}", response_model=AskResponse)
def lire(rid: str) -> AskResponse:
    if rid not in _reponses:
        raise ErreurApi(404, "Réponse introuvable")
    return _reponses[rid]


def _exacte(rid: str) -> ReponseExacte:
    if rid not in _reponses:
        raise ErreurApi(404, "Réponse introuvable")
    rep = _reponses[rid].reponse
    if not isinstance(rep, ReponseExacte):
        raise ErreurApi(409, "Aucune valeur à exporter", "Seule une réponse exacte s'exporte.")
    return rep


@app.get("/v1/answers/{rid}/export.csv")
def export_csv(rid: str, decimale: Literal["point", "virgule"] = "point") -> Response:
    return Response(
        vers_csv(_exacte(rid), virgule_decimale=decimale == "virgule"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="gestukaay-{rid}.csv"'},
    )


@app.get("/v1/answers/{rid}/export.pdf")
def export_pdf(rid: str) -> Response:
    return Response(
        vers_pdf(_exacte(rid)),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="gestukaay-{rid}.pdf"'},
    )


@app.post("/v1/feedback", status_code=204)
def retour(req: FeedbackRequest) -> None:
    if req.reponse_id not in _reponses:
        raise ErreurApi(404, "Réponse introuvable")
