"""Téléchargement borné d'une note vocale (remarque d'Aziz sur #122).

60 s d'Opus pèsent quelques centaines de Ko : au-delà de 2 Mo (le plafond du site), on arrête de lire
au lieu de charger un gros fichier en mémoire. Lecture par morceaux : la taille annoncée peut mentir.
"""

from __future__ import annotations

import httpx

OCTETS_MAX = 2 * 1024 * 1024


class NoteTropGrosse(Exception):
    """Fichier de plus de 2 Mo : le canal invite à reformuler, plus court ou à l'écrit."""


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
