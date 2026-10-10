"""Téléchargement borné d'une note vocale (remarque d'Aziz sur #122), et connexion retentée vers Meta et Telegram.

60 s d'Opus pèsent quelques centaines de Ko : au-delà de 2 Mo (le plafond du site), on arrête de lire
au lieu de charger un gros fichier en mémoire. Lecture par morceaux : la taille annoncée peut mentir.
"""

from __future__ import annotations

import httpx

OCTETS_MAX = 2 * 1024 * 1024
RELANCES = 1  # coupures réseau vers api.telegram.org et graph.facebook.com (essais du 09/10)


class NoteTropGrosse(Exception):
    """Fichier de plus de 2 Mo : le canal invite à reformuler, plus court ou à l'écrit."""


def relance(transport: httpx.BaseTransport | None) -> dict | None:
    """`mounts` d'un client httpx : hors tests (transport simulé), la connexion qui échoue (ConnectError,
    ConnectTimeout) est retentée ; rien n'est encore parti, donc pas de message en double. Un `mounts` plutôt
    qu'un `transport`, qui couperait les proxys de l'environnement. Limite connue (#244) : derrière un proxy
    (HTTPS_PROXY), httpx prend son propre montage `https://`, plus précis, et la connexion n'est pas retentée
    (un montage `https://` à nous ne le remplace pas : vérifié avec httpx 0.28)."""
    return None if transport else {"all://": httpx.HTTPTransport(retries=RELANCES)}


def telecharger(h: httpx.Client, url: str) -> bytes:
    with h.stream("GET", url) as r:
        r.raise_for_status()
        if int(r.headers.get("content-length") or 0) > OCTETS_MAX:
            raise NoteTropGrosse
        morceaux, lu = [], 0
        for m in r.iter_bytes():
            lu += len(m)
            if lu > OCTETS_MAX:
                raise NoteTropGrosse
            morceaux.append(m)
    return b"".join(morceaux)
