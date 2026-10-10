"""Protection de l'API : limite de requêtes par adresse et en-têtes de sécurité.

Limites par minute, par groupe de routes (fenêtre glissante, en mémoire : suffisant pour une seule
instance). Au-delà : 429 au format Problem, avec Retry-After.

Qui est compté (audit du 09/10) : une salle entière derrière le même Wi-Fi, ou tout le trafic derrière un
proxy, partage une seule adresse IP ; compter par adresse revenait à donner 30 questions par minute à tout
le jury. Le site envoie donc, avec chaque POST, un identifiant d'onglet tiré au hasard (en-tête
X-Gestukaay-Client, le même que l'identifiant de conversation) :
  - avec cet en-tête : la limite s'applique à l'onglet, et l'adresse a un plafond de PLAFOND_IP fois la
    limite (un robot qui change d'identifiant à chaque requête reste borné) ;
  - sans lui (curl, robots) : la limite s'applique à l'adresse, comme avant.
Les lectures (catalogue, fiches, séries, exports) restent comptées par adresse, avec des limites larges :
elles ne coûtent rien et n'ont pas besoin de l'en-tête (qui ajouterait une requête CORS préalable).

    GESTUKAAY_LIMITES=off              coupe les limites (tests de bout en bout)
    GESTUKAAY_PROXY_DE_CONFIANCE=1     derrière un proxy (préproduction) : l'adresse est le premier
                                       X-Forwarded-For. Jamais sans proxy : l'en-tête serait falsifiable.
"""

from __future__ import annotations

import os
import re
import threading
import time
from collections import defaultdict, deque

from starlette.requests import Request

# Groupe -> requêtes par minute. Assez large pour un humain pressé, trop étroit pour un robot.
LIMITES: dict[str, int] = {
    "question": 30,  # /v1/ask, /v1/ask/{id}/confirm
    "voix": 10,  # /v1/transcrire : le plus coûteux
    "situer": 30,
    "retour": 20,
    "export": 120,  # lectures par adresse : une salle qui exporte en même temps (audit du 09/10)
    "admin": 20,  # protège aussi le jeton contre les essais à la chaîne
    "ecoute": 120,  # /v1/answers/{id}/audio.ogg : la voix de la réponse, calculée une fois puis gardée (0040)
    "explorer": 300,  # catalogue, fiches et séries : lecture seule, sans LLM, par adresse (une salle entière)
    "suggestions": 600,  # autocomplétion : une requête par pause de frappe, par adresse (une salle qui tape)
}
FENETRE_S = 60.0
# Avec l'identifiant d'onglet : plafond par adresse = PLAFOND_IP × la limite (GESTUKAAY_PLAFOND_IP pour l'ajuster)
PLAFOND_IP = 10
ENTETE_CLIENT = "x-gestukaay-client"
_CLIENT = re.compile(r"[A-Za-z0-9-]{8,64}")


def groupe(chemin: str) -> str | None:
    if chemin.startswith("/v1/ask"):
        return "question"
    if chemin == "/v1/transcrire":
        return "voix"
    if chemin == "/v1/situate":
        return "situer"
    if chemin == "/v1/feedback":
        return "retour"
    if chemin.startswith("/v1/answers/") and chemin.endswith(".ogg"):
        return "ecoute"
    if chemin.startswith("/v1/answers/") and chemin.endswith((".pdf", ".csv")):
        return "export"
    if chemin.startswith("/admin"):
        return "admin"
    if chemin.startswith(("/v1/indicators", "/v1/series", "/v1/carte")):
        return "explorer"
    if chemin == "/v1/suggestions":
        return "suggestions"
    return None  # lecture d'une réponse, santé, documentation : pas de limite


def adresse(requete: Request) -> str:
    if os.environ.get("GESTUKAAY_PROXY_DE_CONFIANCE") == "1":
        transmise = requete.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if transmise:
            return transmise
    return requete.client.host if requete.client else "inconnue"


class Limiteur:
    def __init__(self) -> None:
        self._appels: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._verrou = threading.Lock()

    def attente(self, ip: str, grp: str, maintenant: float | None = None, client: str | None = None) -> float:
        """0 si la requête passe (et elle est comptée), sinon les secondes à attendre.
        client : identifiant d'onglet ; la limite vaut alors pour lui, et l'adresse a un plafond plus large."""
        t = time.monotonic() if maintenant is None else maintenant
        compteurs = [((ip, grp), LIMITES[grp])] if client is None else [
            ((f"{ip}|{client}", grp), LIMITES[grp]), ((ip, f"{grp}:plafond"), LIMITES[grp] * plafond_ip())]
        with self._verrou:
            files = []
            for cle, limite in compteurs:
                appels = self._appels[cle]
                while appels and appels[0] <= t - FENETRE_S:
                    appels.popleft()
                if len(appels) >= limite:
                    return appels[0] + FENETRE_S - t
                files.append(appels)
            for appels in files:  # comptée seulement si elle passe partout
                appels.append(t)
            if len(self._appels) > 50_000:  # garde-fou mémoire : on oublie les adresses inactives
                for cle in [c for c, a in self._appels.items() if not a or a[-1] <= t - FENETRE_S]:
                    del self._appels[cle]
            return 0.0


def client(requete: Request) -> str | None:
    """L'identifiant d'onglet envoyé par le site, s'il est bien formé (sinon : compté par adresse)."""
    valeur = requete.headers.get(ENTETE_CLIENT, "")
    return valeur if _CLIENT.fullmatch(valeur) else None


def plafond_ip() -> int:
    try:
        return max(1, int(os.environ.get("GESTUKAAY_PLAFOND_IP", PLAFOND_IP)))
    except ValueError:
        return PLAFOND_IP


def limites_actives() -> bool:
    return os.environ.get("GESTUKAAY_LIMITES", "on").lower() not in ("off", "0", "non")


# En-têtes ajoutés à toutes les réponses de l'API (JSON, CSV, PDF : rien à exécuter)
ENTETES = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
# La documentation interactive (/docs) charge ses scripts depuis un CDN : pas de CSP stricte là
SANS_CSP = ("/docs", "/redoc", "/openapi.json")
