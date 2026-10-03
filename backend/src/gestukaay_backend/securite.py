"""Protection de l'API : limite de requêtes par adresse et en-têtes de sécurité.

Limites par minute et par adresse IP, par groupe de routes (fenêtre glissante, en mémoire :
suffisant pour une seule instance). Au-delà : 429 au format Problem, avec Retry-After.

    GESTUKAAY_LIMITES=off              coupe les limites (tests de bout en bout)
    GESTUKAAY_PROXY_DE_CONFIANCE=1     derrière un proxy (préproduction) : l'adresse est le premier
                                       X-Forwarded-For. Jamais sans proxy : l'en-tête serait falsifiable.
"""

from __future__ import annotations

import os
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
    "export": 30,
    "admin": 20,  # protège aussi le jeton contre les essais à la chaîne
}
FENETRE_S = 60.0


def groupe(chemin: str) -> str | None:
    if chemin.startswith("/v1/ask"):
        return "question"
    if chemin == "/v1/transcrire":
        return "voix"
    if chemin == "/v1/situate":
        return "situer"
    if chemin == "/v1/feedback":
        return "retour"
    if chemin.startswith("/v1/answers/") and chemin.endswith((".pdf", ".csv")):
        return "export"
    if chemin.startswith("/admin"):
        return "admin"
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

    def attente(self, ip: str, grp: str, maintenant: float | None = None) -> float:
        """0 si la requête passe (et elle est comptée), sinon les secondes à attendre."""
        t = time.monotonic() if maintenant is None else maintenant
        with self._verrou:
            appels = self._appels[(ip, grp)]
            while appels and appels[0] <= t - FENETRE_S:
                appels.popleft()
            if len(appels) >= LIMITES[grp]:
                return appels[0] + FENETRE_S - t
            appels.append(t)
            if len(self._appels) > 50_000:  # garde-fou mémoire : on oublie les adresses inactives
                for cle in [c for c, a in self._appels.items() if not a or a[-1] <= t - FENETRE_S]:
                    del self._appels[cle]
            return 0.0


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
