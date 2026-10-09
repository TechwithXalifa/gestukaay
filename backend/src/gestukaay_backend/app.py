"""API Gëstukaay — squelette de bout en bout (tâche 7.1).

    uv run uvicorn gestukaay_backend.app:app --reload --port 8000

Le backend ne transforme pas la réponse du moteur : il la complète
(`latence_ms`), la stocke et la renvoie telle quelle (contrat-v1 §1).
Stockage : voir stockage.py (GESTUKAAY_BASE, SQLite en mémoire par défaut).
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import logging
import os
import re
import secrets
import threading
import time
from typing import Literal
from urllib.parse import urlencode

from fastapi import BackgroundTasks, Cookie, FastAPI, Form, Header, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
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
from pydantic import BaseModel, Field

from . import comptes, jeu_de_test, securite
from .canaux import Canal, Entrant, Services, charger_canaux
from .exports import SEPARATEUR, TYPE_CSV, encoder_csv, vers_csv, vers_csv_series, vers_pdf
from .stockage import COLONNES_JOURNAL, COLONNES_RETOURS, FiltreJournal, Stockage

app = FastAPI(title="Gëstukaay", version="0.1.0")
ORIGINES = os.environ.get("GESTUKAAY_URL_PUBLIQUE", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINES,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=True,  # cookie de session du back-office (décision 0037)
)

moteur = charger_moteur()
stockage = Stockage()
limiteur = securite.Limiteur()


@app.middleware("http")
async def _proteger(requete: Request, suite):
    """Limite de requêtes par adresse (429 + Retry-After) et en-têtes de sécurité (securite.py)."""
    grp = securite.groupe(requete.url.path)
    if (requete.url.path.startswith("/admin") and requete.method == "POST"
            and requete.headers.get("origin") not in (None, *ORIGINES)):
        # Le back-office tient par un cookie : un POST venu d'un autre site est refusé (CSRF)
        probleme = Problem(title="Origine refusée", status=403)
        return JSONResponse(probleme.model_dump(), status_code=403, media_type="application/problem+json")
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
               confirme_depuis: str | None = None, voix: bool | None = None) -> AskResponse:
    voix = bool(req and req.audio_retour) if voix is None else voix
    # Les URL relèvent du backend (interface.py) : adresse stable du site [EF-29]
    rep.reponse.url = f"{URL_PUBLIQUE.rstrip('/')}/r/{rep.reponse.id}"
    if isinstance(rep.reponse, ReponseExacte):
        # La citation (EF-35) renvoie à la même adresse stable que la réponse
        rep.reponse.citation = _URL_CITEE.sub(rep.reponse.url, rep.reponse.citation)
    # Voix sur le web (décision 0040) : wolof seulement, et calculée à la demande par la route audio.ogg
    rep.reponse.audio_url = f"/v1/answers/{rep.reponse.id}/audio.ogg" if voix and rep.reponse.langue == "wo" else None
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
    return _demander(req)


def _demander(req: AskRequest) -> AskResponse:
    """Chemin commun au web et aux messageries : suivi, réponse du moteur, journal."""
    debut = time.perf_counter()
    # Suivi sur 3 échanges (EF-09, décision 0021) : le moteur reçoit les requêtes précédentes
    contexte = stockage.contexte(req.conversation_id) if req.conversation_id else None
    return _conserver(moteur.repondre(req, contexte), debut, req)


# Opus à 60 s dépasse rarement 600 Ko : 2 Mo laisse de la marge sans ouvrir la porte aux abus
AUDIO_MAX_OCTETS = 2 * 1024 * 1024
FORMATS_AUDIO = {"audio/webm": "webm", "audio/ogg": "ogg"}


@app.post("/v1/transcrire", response_model=TranscriptionResponse)
def transcrire(
    fichier: UploadFile,
    langue: Literal["fr", "wo", "auto"] = Form("auto"),
) -> TranscriptionResponse:
    """Voix sur le web (décision 0004 §1) : audio -> texte, que l'utilisateur
    corrige avant d'envoyer /v1/ask. L'audio n'est jamais écrit sur disque ni
    conservé : il ne vit qu'en mémoire le temps de la transcription (10.7).
    Fonction ordinaire, pas « async » (audit du 09/10) : la transcription attend un service distant
    jusqu'à 17 s (M-Kiriku puis ADIA) avec un client bloquant ; en « async », elle figeait toute l'API
    pendant ce temps. Ici FastAPI la lance dans un fil à part, les autres requêtes continuent."""
    type_mime = (fichier.content_type or "").split(";")[0].strip()
    if type_mime not in FORMATS_AUDIO:
        raise ErreurApi(415, "Format audio non pris en charge", "WebM ou OGG (Opus) attendu.")
    audio = fichier.file.read(AUDIO_MAX_OCTETS + 1)
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
    # Un choix fait après une question vocale garde la voix (décision 0040)
    return _conserver(moteur.executer(choix.requete, rep.question, rep.langue), debut, confirme_depuis=rid,
                      voix=rep.audio_url is not None)


@app.get("/v1/answers/{rid}", response_model=AskResponse)
def lire(rid: str) -> AskResponse:
    return _stockee(rid)


def _exacte(rid: str) -> ReponseExacte:
    rep = _stockee(rid).reponse
    if not isinstance(rep, ReponseExacte):
        raise ErreurApi(409, "Aucune valeur à exporter", "Seule une réponse exacte s'exporte.")
    return rep


# Notes déjà dites, gardées en mémoire pour une réécoute (décision 0040) : jamais sur disque ni journalisées
NOTES_EN_MEMOIRE, NOTES_DUREE_S = 64, 600.0
_notes: dict[str, tuple[float, bytes]] = {}
_verrous_notes: dict[str, threading.Lock] = {}
_verrou_notes = threading.Lock()


def _note(rep: AskResponse) -> bytes | None:
    rid = rep.reponse.id
    with _verrou_notes:
        verrou = _verrous_notes.setdefault(rid, threading.Lock())
    with verrou:  # le navigateur demande souvent deux fois (durée, puis lecture) : une seule synthèse
        maintenant = time.monotonic()
        with _verrou_notes:
            for k in [k for k, (t, _) in _notes.items() if maintenant - t > NOTES_DUREE_S]:
                del _notes[k]
            if rid in _notes:
                return _notes[rid][1]
        try:
            note = moteur.parler(rep)
        finally:
            with _verrou_notes:
                _verrous_notes.pop(rid, None)
        if note is None:
            return None
        with _verrou_notes:
            while len(_notes) >= NOTES_EN_MEMOIRE:
                del _notes[min(_notes, key=lambda k: _notes[k][0])]
            _notes[rid] = (maintenant, note.opus)
        return note.opus


@app.get("/v1/answers/{rid}/audio.ogg")
def audio(rid: str) -> Response:
    """La réponse dite en wolof (EF-16, décision 0040), si la question a été posée à la voix."""
    rep = _stockee(rid)
    if rep.reponse.audio_url is None:
        raise ErreurApi(404, "Pas de voix pour cette réponse")
    try:
        opus = _note(rep)
    except Exception:  # une panne de la voix ne doit jamais casser la réponse : le texte reste
        logging.getLogger("gestukaay.voix").exception("voix : note impossible (réponse %s)", rid)
        opus = None
    if opus is None:
        raise ErreurApi(404, "Voix indisponible", "Le texte reste la réponse.")
    return Response(opus, media_type="audio/ogg", headers={"Cache-Control": "private, max-age=600"})


@app.get("/v1/answers/{rid}/export.csv")
def export_csv(rid: str, decimale: Literal["point", "virgule"] = "point") -> Response:
    return Response(
        vers_csv(_exacte(rid), virgule_decimale=decimale == "virgule"),
        media_type=TYPE_CSV,
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
    rep = moteur.fiche(code)
    # Le moteur cite une adresse provisoire (comme pour les réponses) : la citation EF-35 porte celle du site
    return rep.model_copy(update={"citation": rep.citation.replace("https://app.gestukaay.test", URL_PUBLIQUE.rstrip("/"))})


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
    # Encodé : des codes du référentiel contiennent %, " ou = (bdubwzf.effectif~%)
    params = {"indicateur": indicateur, "zones": ",".join(liste), "debut": debut, "fin": fin}
    url = f"{URL_PUBLIQUE.rstrip('/')}/explorer?" + urlencode({k: v for k, v in params.items() if v})
    fichier = re.sub(r"[^A-Za-z0-9._-]", "_", indicateur)  # nom de fichier toujours bien formé
    return Response(
        vers_csv_series(rep, url, virgule_decimale=decimale == "virgule"),
        media_type=TYPE_CSV,
        headers={"Content-Disposition": f'attachment; filename="gestukaay-{fichier}.csv"'},
    )


@app.post("/v1/feedback", status_code=204)
def retour(req: FeedbackRequest) -> None:
    _stockee(req.reponse_id)
    stockage.retour(req)


# ---------------------------------------------------------------------------
# Back-office : journal des requêtes (hors contrat public, réservé à l'équipe)
# ---------------------------------------------------------------------------


COOKIE_ADMIN = "gestukaay_admin"


def _admin(session: str | None) -> str:
    """L'identifiant de la session du back-office (comptes.py, décision 0037). Sans compte actif,
    le back-office n'existe pas (404)."""
    if not stockage.back_office_ouvert():
        raise ErreurApi(404, "Not Found")
    identifiant = comptes.identifier(stockage, session)
    if not identifiant:
        raise ErreurApi(401, "Connexion requise")
    return identifiant


class Connexion(BaseModel):
    identifiant: str = Field(max_length=64)
    mot_de_passe: str = Field(max_length=256)


@app.post("/admin/connexion")
def connexion(corps: Connexion, reponse: Response) -> dict:
    """Identifiant et mot de passe ; ouvre une session portée par un cookie HttpOnly."""
    if not stockage.back_office_ouvert():
        raise ErreurApi(404, "Not Found")
    jeton = comptes.connecter(stockage, corps.identifiant, corps.mot_de_passe)
    if not jeton:
        raise ErreurApi(401, "Identifiant ou mot de passe incorrect",
                        f"Après {comptes.ESSAIS_MAX} essais manqués, le compte est bloqué 15 minutes.")
    reponse.set_cookie(COOKIE_ADMIN, jeton, max_age=int(comptes.DUREE_MAX.total_seconds()), path="/admin",
                       httponly=True, samesite="strict", secure=URL_PUBLIQUE.startswith("https://"))
    return {"identifiant": comptes.identifier(stockage, jeton)}


@app.post("/admin/deconnexion", status_code=204)
def deconnexion(reponse: Response, session: str | None = Cookie(None, alias=COOKIE_ADMIN)) -> None:
    if session:
        stockage.fermer_session(session)
    reponse.delete_cookie(COOKIE_ADMIN, path="/admin", httponly=True, samesite="strict",
                          secure=URL_PUBLIQUE.startswith("https://"))


@app.get("/admin/moi")
def moi(session: str | None = Cookie(None, alias=COOKIE_ADMIN)) -> dict:
    """La personne connectée : le site sait s'il doit montrer le formulaire de connexion."""
    return {"identifiant": _admin(session)}


def _filtre(issue: str | None, canal: str | None, langue: str | None, q: str | None, retour: str | None,
            limite: int, decalage: int) -> FiltreJournal:
    return FiltreJournal(issue=issue, canal=canal, langue=langue, texte=q, retour=retour, limite=limite,
                         decalage=decalage)


def _cellule(valeur):
    """Export ouvert dans un tableur : un texte saisi par l'usager (question, commentaire, suggestion) qui
    commence par = + - @ y deviendrait une formule (injection CSV). Une apostrophe le garde en texte."""
    return f"'{valeur}" if isinstance(valeur, str) and valeur[:1] in ("=", "+", "-", "@", "\t", "\r") else valeur


@app.get("/admin/journal")
def journal(
    session: str | None = Cookie(None, alias=COOKIE_ADMIN),
    issue: Literal["exacte", "approchee", "aucune"] | None = None,
    canal: str | None = None,
    langue: str | None = None,
    q: str | None = Query(None, max_length=100),
    retour: Literal["signale", "pas_utile", "utile", "suggere"] | None = None,
    limite: int = Query(50, ge=1, le=500),
    decalage: int = Query(0, ge=0),
) -> dict:
    _admin(session)
    total, lignes = stockage.journal(_filtre(issue, canal, langue, q, retour, limite, decalage))
    return {"total": total, "lignes": lignes}


@app.get("/admin/tableau")
def tableau(
    session: str | None = Cookie(None, alias=COOKIE_ADMIN),
    jours: int = Query(30),
    canal: str | None = None,
    langue: str | None = None,
) -> dict:
    """Tableau de bord (US-28) : questions, issues, latence médiane et p95, part du wolof,
    satisfaction, signalements, questions non résolues les plus fréquentes."""
    _admin(session)
    if jours not in (7, 30, 90):
        raise ErreurApi(422, "Période inconnue", "jours = 7, 30 ou 90.")
    # Exactitude et refus pertinents (US-28) : la dernière exécution terminée du jeu de test
    derniere = next((e for e in stockage.executions() if e["statut"] == "terminee" and e["resultat"]), None)
    return {**stockage.tableau(jours, canal or None, langue or None),
            "benchmark": {"lancee_le": derniere["lancee_le"], **jeu_de_test.resume(derniere["resultat"])} if derniere else None}


# Jeu de test (cahier 5.10, maquette BO-JeuTest) : le benchmark de KBD lancé depuis le back-office
def _en_fond(tache) -> None:
    threading.Thread(target=tache, name="benchmark", daemon=True).start()


executer_benchmark = _en_fond  # remplacé dans les tests par un appel direct


@app.get("/admin/jeu-de-test")
def jeu_de_test_liste(session: str | None = Cookie(None, alias=COOKIE_ADMIN)) -> dict:
    """Les questions de référence et les exécutions du benchmark (résumés, plus récentes d'abord)."""
    _admin(session)
    return {
        "disponible": jeu_de_test.moteur_pour(moteur, "regles") is not None,
        "llm_autorise": jeu_de_test.llm_autorise(),
        "questions": jeu_de_test.resume_questions(),
        "executions": [{**{k: e[k] for k in ("id", "mode", "lancee_le", "statut", "erreur")},
                        "resume": jeu_de_test.resume(e["resultat"]) if e["resultat"] else None}
                       for e in stockage.executions()],
    }


@app.get("/admin/jeu-de-test/executions/{eid}")
def jeu_de_test_execution(eid: str, session: str | None = Cookie(None, alias=COOKIE_ADMIN)) -> dict:
    """Une exécution complète : chaque question avec son issue, son statut et le détail de l'écart."""
    _admin(session)
    execution = next((e for e in stockage.executions() if e["id"] == eid), None)
    if execution is None:
        raise ErreurApi(404, "Exécution introuvable")
    return execution


@app.post("/admin/jeu-de-test/executions", status_code=202)
def jeu_de_test_lancer(corps: dict, session: str | None = Cookie(None, alias=COOKIE_ADMIN)) -> dict:
    """Lance le benchmark en tâche de fond. « llm » appelle la chaîne LLM (environ 0,07 $)."""
    _admin(session)
    mode = corps.get("mode")
    if mode not in jeu_de_test.MODES:
        raise ErreurApi(422, "Mode inconnu", "mode = regles ou llm.")
    if mode == "llm" and not jeu_de_test.llm_autorise():
        raise ErreurApi(403, "Désactivé sur ce serveur",
                        "Le benchmark avec le LLM demande GESTUKAAY_BENCHMARK_LLM=oui (coût, moteur occupé).")
    m = jeu_de_test.moteur_pour(moteur, mode)
    if m is None:
        raise ErreurApi(503, "Pas disponible", "Le benchmark demande le moteur réel (GESTUKAAY_MOTEUR=reel).")
    try:
        eid = jeu_de_test.lancer(executer_benchmark, stockage, mode, m)
    except RuntimeError as e:
        raise ErreurApi(409, "Exécution en cours", "Attendez la fin de l'exécution en cours.") from e
    return {"id": eid, "statut": "en_cours"}


@app.get("/admin/journal.csv")
def journal_csv(
    session: str | None = Cookie(None, alias=COOKIE_ADMIN),
    issue: Literal["exacte", "approchee", "aucune"] | None = None,
    canal: str | None = None,
    langue: str | None = None,
    q: str | None = Query(None, max_length=100),
    retour: Literal["signale", "pas_utile", "utile", "suggere"] | None = None,
) -> Response:
    _admin(session)
    _, lignes = stockage.journal(_filtre(issue, canal, langue, q, retour, 100_000, 0))
    sortie = io.StringIO()
    w = csv.DictWriter(sortie, [*COLONNES_JOURNAL, *COLONNES_RETOURS], delimiter=SEPARATEUR, lineterminator="\r\n")
    w.writeheader()
    w.writerows({k: _cellule(v) for k, v in ligne.items()} for ligne in lignes)
    return Response(
        encoder_csv(sortie.getvalue()),  # même format Excel que les exports de réponse
        media_type=TYPE_CSV,
        headers={"Content-Disposition": 'attachment; filename="gestukaay-journal.csv"'},
    )


# ---------------------------------------------------------------------------
# Webhooks WhatsApp et Telegram (EF-19, EF-24, 10.7). Transport ici (SAN) ; lecture, interprétation,
# mise en forme et envoi dans le module de canal (KBD), par l'interface de canaux.py.
# ---------------------------------------------------------------------------

canaux: dict[str, Canal] = charger_canaux()
_log_webhooks = logging.getLogger("gestukaay.webhooks")


def _services(nom: str, expediteur: str) -> Services:
    """Les services d'une conversation : même chemin que le web, numéro haché par le stockage."""
    conversation = f"{nom}:{expediteur}"

    def demander_(question: str, *, langue: str = "auto", source: str = "texte",
                  transcription_brute: str | None = None, audio_retour: bool = False) -> AskResponse:
        return _demander(AskRequest(question=question, langue=langue, canal=nom, conversation_id=conversation,
                                    source=source, transcription_brute=transcription_brute,
                                    audio_retour=audio_retour))

    return Services(
        conversation_id=conversation,
        demander=demander_,
        confirmer=lambda rid, choix_id: confirmer(rid, ConfirmRequest(choix_id=choix_id)),
        derniere=lambda: stockage.derniere(conversation),
        transcrire=lambda audio, format_audio: moteur.transcrire(audio, format_audio, "auto"),
        parler=lambda rep: moteur.parler(rep),
    )


def _traiter(canal: Canal, entrant: Entrant) -> None:
    """Tâche de fond : une erreur est journalisée (sans le numéro), jamais renvoyée à Meta."""
    try:
        canal.traiter(entrant, _services(canal.nom, entrant.expediteur))
    except Exception:  # noqa: BLE001 — tâche de fond : tout est journalisé, rien ne remonte à Meta
        _log_webhooks.exception("%s : échec du traitement du message %s", canal.nom, entrant.message_id)


def _recevoir(nom: str, corps: bytes, taches: BackgroundTasks) -> dict:
    """Lit le payload, écarte les messages déjà reçus, planifie le reste. Toujours 200 ensuite :
    un payload inattendu est journalisé, pas renvoyé en erreur (Meta le renverrait en boucle)."""
    canal = canaux[nom]
    try:
        entrants = canal.lire(json.loads(corps))
    except Exception:  # noqa: BLE001 — payload inattendu : journalisé, 200 pour que Meta ne le renvoie pas
        _log_webhooks.exception("%s : payload illisible", nom)
        return {"statut": "ignore"}
    nouveaux = [e for e in entrants if stockage.premier_passage(nom, e.message_id)]
    for e in nouveaux:
        taches.add_task(_traiter, canal, e)
    return {"statut": "recu", "messages": len(nouveaux)}


def _canal_ouvert(nom: str, secret: str | None) -> str:
    """Sans module de canal ou sans secret configuré, le webhook n'existe pas (404)."""
    if nom not in canaux or not secret:
        raise ErreurApi(404, "Not Found")
    return secret


@app.get("/webhooks/whatsapp")
def whatsapp_verification(
    mode: str | None = Query(None, alias="hub.mode"),
    jeton: str | None = Query(None, alias="hub.verify_token"),
    defi: str | None = Query(None, alias="hub.challenge"),
) -> PlainTextResponse:
    """Vérification de l'abonnement par Meta : renvoyer hub.challenge si le jeton est le bon."""
    attendu = _canal_ouvert("whatsapp", os.environ.get("WHATSAPP_VERIFY_TOKEN"))
    if mode == "subscribe" and jeton and defi and secrets.compare_digest(jeton, attendu):
        return PlainTextResponse(defi)
    raise ErreurApi(403, "Vérification refusée")


@app.post("/webhooks/whatsapp")
async def whatsapp(requete: Request, taches: BackgroundTasks,
                   signature: str | None = Header(None, alias="X-Hub-Signature-256")) -> dict:
    """Messages WhatsApp : signature HMAC-SHA256 du corps brut avec WHATSAPP_APP_SECRET, comparée en
    temps constant (403 sinon) ; 200 immédiat, traitement en tâche de fond."""
    secret = _canal_ouvert("whatsapp", os.environ.get("WHATSAPP_APP_SECRET"))
    corps = await requete.body()
    attendue = "sha256=" + hmac.new(secret.encode(), corps, hashlib.sha256).hexdigest()
    if not signature or not secrets.compare_digest(signature, attendue):
        raise ErreurApi(403, "Signature invalide")
    return await run_in_threadpool(_recevoir, "whatsapp", corps, taches)  # la base hors de la boucle


@app.post("/webhooks/telegram")
async def telegram(requete: Request, taches: BackgroundTasks,
                   jeton: str | None = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")) -> dict:
    """Bot Telegram de secours (EF-24) : jeton secret fixé à setWebhook (secret_token), comparé en
    temps constant ; même traitement que WhatsApp."""
    attendu = _canal_ouvert("telegram", os.environ.get("TELEGRAM_SECRET_TOKEN"))
    if not jeton or not secrets.compare_digest(jeton, attendu):
        raise ErreurApi(403, "Jeton invalide")
    return await run_in_threadpool(_recevoir, "telegram", await requete.body(), taches)
