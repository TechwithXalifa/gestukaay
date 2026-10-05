"""Ce qu'on fait d'un message reçu, commun à WhatsApp et Telegram (décision 0025).

  - premier message de la conversation : l'accueil d'abord ;
  - commande seule (« ndimbal », « exemples », « stop »…) : le texte fixe ;
  - « non », « déet », « waxuma loolu deh »… : on a mal compris, on invite à reformuler (US-09) ;
  - choix « 1 », « benn », ou un toucher dans la liste : confirmer le choix de la dernière réponse
    approchée (EF-06) ; sans approchée en attente, « choix invalide » ;
  - note vocale : transcription si elle existe (#28), sinon « je ne sais pas encore écouter » ;
  - question : le moteur, par le même chemin que le web (suivi, journal, lien /r/{id}).
Une erreur envoie le texte « erreur » puis remonte au backend, qui la journalise sans le numéro.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from gestukaay_backend.canaux import Entrant, Services
from gestukaay_contracts.models import Choix, ReponseApprochee
from gestukaay_engine import NonDisponible

from .format import Sortant, formater
from .textes import commande, texte


@dataclass(frozen=True)
class Contenu:
    """Ce que `lire` garde d'un message : son type et ce qu'il faut pour le traiter."""

    type: Literal["texte", "audio", "choix", "autre"]
    texte: str = ""
    media: str = ""  # identifiant du média (WhatsApp : media id ; Telegram : file_id)
    choix_id: str = ""
    accuse: str = ""  # identifiant à accuser (WhatsApp : wamid ; Telegram : callback_query id)


class Envoyeur(Protocol):
    gras: bool

    def accuser(self, destinataire: str, contenu: Contenu) -> None: ...
    def texte(self, destinataire: str, texte: str) -> None: ...
    def choix(self, destinataire: str, choix: list[Choix]) -> None: ...
    def media(self, contenu: Contenu) -> bytes: ...


def traiter(entrant: Entrant, services: Services, envoyeur: Envoyeur) -> None:
    dest, c = entrant.expediteur, entrant.contenu
    envoyeur.accuser(dest, c)
    try:
        if services.derniere() is None:
            envoyeur.texte(dest, texte("accueil"))
        _repondre(dest, c, services, envoyeur)
    except Exception:
        envoyeur.texte(dest, texte("erreur"))
        raise


def _repondre(dest: str, c: Contenu, services: Services, envoyeur: Envoyeur) -> None:
    if c.type == "choix":
        return _choisir(dest, c.choix_id, services, envoyeur)
    if c.type == "audio":
        try:
            tr = services.transcrire(envoyeur.media(c), "ogg")
        except NonDisponible:
            return envoyeur.texte(dest, texte("vocal_pas_encore"))
        if not tr.transcription.strip():  # rien d'audible ou de compris
            return envoyeur.texte(dest, texte("reformuler"))
        rep = services.demander(tr.transcription, source="voix", transcription_brute=tr.transcription)
        return _envoyer(dest, formater(rep, envoyeur.gras), envoyeur)
    if c.type != "texte" or not c.texte.strip():
        return envoyeur.texte(dest, texte("aide"))
    cmd = commande(c.texte)
    if cmd in ("1", "2", "3"):
        return _choisir(dest, cmd, services, envoyeur)
    if cmd == "non":
        return envoyeur.texte(dest, texte("reformuler"))
    if cmd:
        return envoyeur.texte(dest, texte(cmd))
    if len(c.texte.strip()) < 3:  # « ok », « ?? » : trop court pour une question (contrat : 3 caractères)
        return envoyeur.texte(dest, texte("aide"))
    _envoyer(dest, formater(services.demander(c.texte.strip()[:300]), envoyeur.gras), envoyeur)


def _choisir(dest: str, choix_id: str, services: Services, envoyeur: Envoyeur) -> None:
    derniere = services.derniere()
    r = derniere.reponse if derniere else None
    if not isinstance(r, ReponseApprochee) or choix_id not in {x.id for x in r.choix}:
        return envoyeur.texte(dest, texte("choix_invalide"))
    _envoyer(dest, formater(services.confirmer(r.id, choix_id), envoyeur.gras), envoyeur)


def _envoyer(dest: str, s: Sortant, envoyeur: Envoyeur) -> None:
    envoyeur.texte(dest, s.texte)
    if s.choix:
        envoyeur.choix(dest, s.choix)
