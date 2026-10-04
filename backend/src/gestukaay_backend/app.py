"""API Gëstukaay — squelette de bout en bout (tâche 7.1).

    uv run uvicorn gestukaay_backend.app:app --reload --port 8000

Le backend ne transforme pas la réponse du moteur : il la complète
(`latence_ms`), la stocke et la renvoie telle quelle (contrat-v1 §1).
Stockage : voir stockage.py (GESTUKAAY_BASE, SQLite en mémoire par défaut).
"""

from __future__ import annotations

import csv
import io
import os
import re
import secrets
import time
from typing import Literal

from fastapi import FastAPI, Form, Header, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from gestukaay_contracts.models import (
    AskRequest,
    AskResponse,
    CatalogueResponse,
    ConfirmRequest,
    FeedbackRequest,
    FicheIndicateur,
    Problem,
    ReponseApprochee,
    ReponseExacte,
    SeriesResponse,
    SituateRequest,
    SituateResponse,
    TranscriptionResponse,
)
from gestukaay_engine import IndicateurInconnu, NonDisponible, SaisieInvalide, charger_moteur

from . import securite
from .exports import vers_csv, vers_csv_series, vers_pdf
from .stockage import COLONNES_JOURNAL, FiltreJournal, Stockage

app = FastAPI(title="Gëstukaay", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("GESTUKAAY_URL_PUBLIQUE", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

moteur = charger_moteur()
stockage = Stockage()
limiteur = securite.Limiteur()


@app.middleware("http")
async def _proteger(requete: Request, suite):
    """Limite de requêtes par adresse (429 + Retry-After) et en-têtes de sécurité (securite.py)."""
    grp = securite.groupe(requete.url.path)
    if grp and requete.method != "OPTIONS" and securite.limites_actives():
        attente = limiteur.attente(securite.adresse(requete), grp)
        if attente:
            probleme = Problem(title="Trop de requêtes", status=429,
                               detail="Patientez un instant avant de réessayer.")
            return JSONResponse(probleme.model_dump(), status_code=429, media_type="application/problem+json",
                                headers={"Retry-After": str(max(1, round(attente)))})
    reponse = await suite(requete)
    for nom, valeur in securite.ENTETES.items():
        if nom == "Content-Security-Policy" and requete.url.path.startswith(securite.SANS_CSP):
            continue
        reponse.headers.setdefault(nom, valeur)
    if requete.url.path.startswith("/admin"):
        reponse.headers["Cache-Control"] = "no-store"  # le journal ne doit rester dans aucun cache
    return reponse


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


@app.exception_handler(NonDisponible)
async def _non_disponible(_: Request, exc: NonDisponible) -> JSONResponse:
    """Fonction pas encore construite dans le moteur réel (voix, « Où je me situe ») : 503,
    jamais 500 ni les chiffres fixes du faux moteur (décision 0019). Le site affiche déjà
    l'état « Le service ne répond pas » avec Réessayer."""
    probleme = Problem(title="Pas encore disponible", status=503,
                       detail="Cette fonction n'est pas encore disponible. Réessayez plus tard.")
    return JSONResponse(probleme.model_dump(), status_code=503, media_type="application/problem+json")


@app.exception_handler(SaisieInvalide)
async def _saisie_invalide(_: Request, exc: SaisieInvalide) -> JSONResponse:
    """Saisie hors du référentiel (« Où je me situe » : région inconnue, département, pays) : 422,
    comme une saisie mal formée. Le détail du moteur ne cite que la région envoyée : rien d'interne."""
    probleme = Problem(title="Saisie invalide", status=422, detail=str(exc))
    return JSONResponse(probleme.model_dump(), status_code=422, media_type="application/problem+json")


@app.exception_handler(IndicateurInconnu)
async def _indicateur_inconnu(_: Request, exc: IndicateurInconnu) -> JSONResponse:
    probleme = Problem(title="Indicateur introuvable", status=404, detail=f"Aucun indicateur {exc}.")
    return JSONResponse(probleme.model_dump(), status_code=404, media_type="application/problem+json")


_URL_CITEE = re.compile(r"https?://\S+?/r/[\w-]+")
URL_PUBLIQUE = os.environ.get("GESTUKAAY_URL_PUBLIQUE", "http://localhost:3000").split(",")[0]


def _conserver(rep: AskResponse, debut: float, req: AskRequest | None = None,
               confirme_depuis: str | None = None) -> AskResponse:
    # Les URL relèvent du backend (interface.py) : adresse stable du site [EF-29]
    rep.reponse.url = f"{URL_PUBLIQUE.rstrip('/')}/r/{rep.reponse.id}"
    if isinstance(rep.reponse, ReponseExacte):
        # La citation (EF-35) renvoie à la même adresse stable que la réponse
        rep.reponse.citation = _URL_CITEE.sub(rep.reponse.url, rep.reponse.citation)
    rep.reponse.latence_ms = round((time.perf_counter() - debut) * 1000)
    stockage.enregistrer(rep, req, confirme_depuis)
    return rep


def _stockee(rid: str) -> AskResponse:
    rep = stockage.lire(rid)
    if rep is None:
        raise ErreurApi(404, "Réponse introuvable")
    return rep


@app.get("/health")
def sante() -> dict:
    return {"statut": "ok", "version_socle": moteur.version_socle()}


@app.post("/v1/ask", response_model=AskResponse)
def demander(req: AskRequest) -> AskResponse:
    debut = time.perf_counter()
    # Suivi sur 3 échanges (EF-09, décision 0021) : le moteur reçoit les requêtes précédentes
    contexte = stockage.contexte(req.conversation_id) if req.conversation_id else None
    return _conserver(moteur.repondre(req, contexte), debut, req)


# Opus à 60 s dépasse rarement 600 Ko : 2 Mo laisse de la marge sans ouvrir la porte aux abus
AUDIO_MAX_OCTETS = 2 * 1024 * 1024
FORMATS_AUDIO = {"audio/webm": "webm", "audio/ogg": "ogg"}


@app.post("/v1/transcrire", response_model=TranscriptionResponse)
async def transcrire(
    fichier: UploadFile,
    langue: Literal["fr", "wo", "auto"] = Form("auto"),
) -> TranscriptionResponse:
    """Voix sur le web (décision 0004 §1) : audio -> texte, que l'utilisateur
    corrige avant d'envoyer /v1/ask. L'audio n'est jamais écrit sur disque ni
    conservé : il ne vit qu'en mémoire le temps de la transcription (10.7)."""
    type_mime = (fichier.content_type or "").split(";")[0].strip()
    if type_mime not in FORMATS_AUDIO:
        raise ErreurApi(415, "Format audio non pris en charge", "WebM ou OGG (Opus) attendu.")
    audio = await fichier.read(AUDIO_MAX_OCTETS + 1)
    if len(audio) > AUDIO_MAX_OCTETS:
        raise ErreurApi(413, "Enregistrement trop long", "60 secondes au maximum.")
    if not audio:
        raise ErreurApi(422, "Enregistrement vide")
    try:
        return moteur.transcrire(audio, FORMATS_AUDIO[type_mime], langue)
    finally:
        del audio


@app.post("/v1/situate", response_model=SituateResponse)
def situer(req: SituateRequest) -> SituateResponse:
    """« Où je me situe » (décision 0004 §2). RIEN n'est conservé : ni stockage,
    ni journal, ni identifiant (EF-40, US-21). Ne jamais journaliser `req`."""
    return moteur.situer(req)


@app.post("/v1/ask/{rid}/confirm", response_model=AskResponse)
def confirmer(rid: str, req: ConfirmRequest) -> AskResponse:
    debut = time.perf_counter()
    rep = _stockee(rid).reponse
    if not isinstance(rep, ReponseApprochee):
        raise ErreurApi(409, "Cette réponse n'attend pas de confirmation")
    choix = next((c for c in rep.choix if c.id == req.choix_id), None)
    if choix is None:
        raise ErreurApi(422, "Choix inconnu", f"choix_id={req.choix_id!r}")
    return _conserver(moteur.executer(choix.requete, rep.question, rep.langue), debut, confirme_depuis=rid)


@app.get("/v1/answers/{rid}", response_model=AskResponse)
def lire(rid: str) -> AskResponse:
    return _stockee(rid)


def _exacte(rid: str) -> ReponseExacte:
    rep = _stockee(rid).reponse
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


# ---------------------------------------------------------------------------
# v1.4.0 — Catalogue, fiche indicateur et séries d'Explorer (décision 0023)
# ---------------------------------------------------------------------------

ZONES_MAX = 6  # [US-18] « jusqu'à 6 zones »


@app.get("/v1/indicators", response_model=CatalogueResponse)
def catalogue(
    domaine: str | None = Query(None, max_length=80),
    q: str | None = Query(None, max_length=100),
    niveau: Literal["pays", "region", "departement", "academie"] | None = None,
    limite: int = Query(50, ge=1, le=100),
    decalage: int = Query(0, ge=0),
) -> CatalogueResponse:
    return moteur.catalogue(domaine or None, (q or "").strip() or None, niveau, limite, decalage)


@app.get("/v1/indicators/{code}", response_model=FicheIndicateur)
def fiche(code: str) -> FicheIndicateur:
    return moteur.fiche(code)


def _zones(zones: str) -> list[str]:
    liste = list(dict.fromkeys(z.strip() for z in zones.split(",") if z.strip()))
    if not liste:
        raise ErreurApi(422, "Aucune zone", "Choisissez au moins une zone.")
    if len(liste) > ZONES_MAX:
        raise ErreurApi(422, "Trop de zones", f"{ZONES_MAX} zones au plus.")
    return liste


@app.get("/v1/series", response_model=SeriesResponse)
def series(
    indicateur: str = Query(..., max_length=120),
    zones: str = Query("SN", max_length=200),
    debut: str | None = Query(None, max_length=10),
    fin: str | None = Query(None, max_length=10),
) -> SeriesResponse:
    """Séries publiées pour Explorer : jamais d'interpolation, les zones sans valeur dans `absents`."""
    return moteur.series(indicateur, _zones(zones), debut or None, fin or None)


@app.get("/v1/series.csv")
def series_csv(
    indicateur: str = Query(..., max_length=120),
    zones: str = Query("SN", max_length=200),
    debut: str | None = Query(None, max_length=10),
    fin: str | None = Query(None, max_length=10),
    decimale: Literal["point", "virgule"] = "point",
) -> Response:
    """Export CSV de la vue Explorer (schéma EF-34), avec l'adresse stable de cette vue (EF-29)."""
    liste = _zones(zones)
    rep = moteur.series(indicateur, liste, debut or None, fin or None)
    params = {"indicateur": indicateur, "zones": ",".join(liste), "debut": debut or "", "fin": fin or ""}
    url = f"{URL_PUBLIQUE.rstrip('/')}/explorer?" + "&".join(f"{k}={v}" for k, v in params.items() if v)
    return Response(
        vers_csv_series(rep, url, virgule_decimale=decimale == "virgule"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="gestukaay-{indicateur}.csv"'},
    )


@app.post("/v1/feedback", status_code=204)
def retour(req: FeedbackRequest) -> None:
    _stockee(req.reponse_id)
    stockage.retour(req)


# ---------------------------------------------------------------------------
# Back-office : journal des requêtes (hors contrat public, réservé à l'équipe)
# ---------------------------------------------------------------------------


def _admin(authorization: str | None) -> None:
    """Jeton GESTUKAAY_ADMIN_JETON. Sans jeton configuré, le back-office n'existe pas (404)."""
    jeton = os.environ.get("GESTUKAAY_ADMIN_JETON")
    if not jeton:
        raise ErreurApi(404, "Not Found")
    if not authorization or not secrets.compare_digest(authorization, f"Bearer {jeton}"):
        raise ErreurApi(401, "Jeton d'administration requis")


def _filtre(issue: str | None, canal: str | None, langue: str | None, q: str | None,
            limite: int, decalage: int) -> FiltreJournal:
    return FiltreJournal(issue=issue, canal=canal, langue=langue, texte=q, limite=limite, decalage=decalage)


@app.get("/admin/journal")
def journal(
    authorization: str | None = Header(None),
    issue: Literal["exacte", "approchee", "aucune"] | None = None,
    canal: str | None = None,
    langue: str | None = None,
    q: str | None = Query(None, max_length=100),
    limite: int = Query(50, ge=1, le=500),
    decalage: int = Query(0, ge=0),
) -> dict:
    _admin(authorization)
    total, lignes = stockage.journal(_filtre(issue, canal, langue, q, limite, decalage))
    return {"total": total, "lignes": lignes}


@app.get("/admin/tableau")
def tableau(
    authorization: str | None = Header(None),
    jours: int = Query(30),
    canal: str | None = None,
    langue: str | None = None,
) -> dict:
    """Tableau de bord (US-28) : questions, issues, latence médiane et p95, part du wolof,
    satisfaction, signalements, questions non résolues les plus fréquentes."""
    _admin(authorization)
    if jours not in (7, 30, 90):
        raise ErreurApi(422, "Période inconnue", "jours = 7, 30 ou 90.")
    return stockage.tableau(jours, canal or None, langue or None)


@app.get("/admin/journal.csv")
def journal_csv(
    authorization: str | None = Header(None),
    issue: Literal["exacte", "approchee", "aucune"] | None = None,
    canal: str | None = None,
    langue: str | None = None,
    q: str | None = Query(None, max_length=100),
) -> Response:
    _admin(authorization)
    _, lignes = stockage.journal(_filtre(issue, canal, langue, q, 100_000, 0))
    sortie = io.StringIO()
    w = csv.DictWriter(sortie, [*COLONNES_JOURNAL, "vote", "signalement", "suggestions"], delimiter=";")
    w.writeheader()
    w.writerows(lignes)
    return Response(
        "﻿" + sortie.getvalue(),  # BOM : Excel ouvre l'UTF-8 correctement
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="gestukaay-journal.csv"'},
    )
