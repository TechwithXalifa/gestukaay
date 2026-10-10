"""Ce qu'on fait d'un message reçu, commun à WhatsApp et Telegram (décision 0025).

  - premier message de la conversation : l'accueil d'abord ;
  - commande seule (« ndimbal », « exemples », « stop »…) : le texte fixe ;
  - « non », « déet », « waxuma loolu deh »… : on a mal compris, on invite à reformuler (US-09) ;
  - choix « 1 », « benn », ou un toucher dans la liste : confirmer le choix de la dernière réponse
    approchée (EF-06) ; sans approchée en attente, « choix invalide » ;
  - note vocale : transcription si elle existe (#28), sinon « je ne sais pas encore écouter » ;
  - question : le moteur, par le même chemin que le web (suivi, journal, lien /r/{id}) ;
  - réponse dans le mode de la question (choix de KBD, 07/10, décision 0029) : question écrite (français
    ou wolof) -> le texte seul ; question vocale en wolof -> la note vocale en wolof (EF-20) puis une fiche d'une
    ligne (chiffre exact et source) et, pour une approchée, les choix ; question vocale en français -> le texte
    complet en français (pas de voix française, KBD 08/10) ; si la voix manque ou tombe en
    panne, le texte complet, comme pour une question écrite.
Une erreur envoie le texte « erreur » puis remonte au backend, qui la journalise sans le numéro ; une
panne de la voix (calcul ou envoi) est journalisée et le texte complet part à la place ; un accusé (lu, « en
train d'écrire ») refusé ou injoignable est journalisé et la réponse part quand même (essais du 09/10 : un 400 de
Meta et une coupure réseau vers Telegram bloquaient toute réponse).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Protocol

from gestukaay_backend.canaux import Entrant, Services
from gestukaay_contracts.models import AskResponse, Choix, ReponseApprochee
from gestukaay_engine import NonDisponible

from .format import Sortant, fiche, formater
from .media import NoteTropGrosse
from .textes import commande, est_salutation, texte


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
    def choix(self, destinataire: str, choix: list[Choix], message: str) -> None: ...  # un seul message
    def media(self, contenu: Contenu) -> bytes: ...
    def preparer_vocal(self, destinataire: str) -> None: ...  # « enregistre un audio… » si le canal le sait
    def vocal(self, destinataire: str, opus: bytes) -> None: ...  # note vocale OGG/Opus


_log = logging.getLogger("gestukaay.canaux")


def traiter(entrant: Entrant, services: Services, envoyeur: Envoyeur) -> None:
    dest, c = entrant.expediteur, entrant.contenu
    try:
        envoyeur.accuser(dest, c)
    except Exception as e:  # noqa: BLE001 — l'accusé n'est qu'un confort : il ne doit jamais empêcher la réponse
        # le motif précis est journalisé par le canal (WhatsApp : code et motif de Meta, juste avant) ; ici, ni
        # l'adresse de l'API ni le numéro
        _log.warning("accusé non envoyé, la réponse suit quand même (%s)", type(e).__name__)
    try:
        if c.type == "texte" and est_salutation(c.texte):  # « /start », « Salam naka leu » : l'accueil seul
            return envoyeur.texte(dest, texte("accueil"))
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
        except NoteTropGrosse:  # plus de 2 Mo : bien au-delà des 60 s permises
            return envoyeur.texte(dest, texte("reformuler"))
        if not tr.transcription.strip():  # rien d'audible ou de compris
            return envoyeur.texte(dest, texte("reformuler"))
        # EF-15, US-07, P1 étape 3 : la transcription comprise d'abord, pour que l'utilisateur voie ce qui a été
        # entendu et puisse répondre « non » / « déet » (US-09) ; la réponse suit
        envoyeur.texte(dest, f"{texte('compris')} « {tr.transcription.strip()} »")
        rep = services.demander(tr.transcription, source="voix", transcription_brute=tr.transcription,
                                audio_retour=True)
        return _envoyer(dest, rep, services, envoyeur)
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
    _envoyer(dest, services.demander(c.texte.strip()[:300]), services, envoyeur)  # écrite : texte seul


def _choisir(dest: str, choix_id: str, services: Services, envoyeur: Envoyeur) -> None:
    derniere = services.derniere()
    r = derniere.reponse if derniere else None
    if not isinstance(r, ReponseApprochee) or choix_id not in {x.id for x in r.choix}:
        return envoyeur.texte(dest, texte("choix_invalide"))
    _envoyer(dest, services.confirmer(r.id, choix_id), services, envoyeur)


def _envoyer(dest: str, rep: AskResponse, services: Services, envoyeur: Envoyeur) -> None:
    s: Sortant = formater(rep, envoyeur.gras)
    # la voix est en wolof (EF-20, seule voix du projet) : une question vocale en français reçoit le texte complet,
    # en français (choix de KBD, 08/10 : une note wolof répondait à une question posée en français)
    vocal = rep.reponse.transcription is not None and rep.reponse.langue == "wo" and _dire(dest, rep, services, envoyeur)
    if s.choix:  # approchée : le texte et les boutons en UN message (#213 : les choix partaient deux fois)
        try:
            envoyeur.choix(dest, s.choix, s.texte)
        except Exception:  # noqa: BLE001 — liste ou boutons refusés : le texte numéroté suffit pour répondre (revue de SAN)
            _log.exception("choix : la liste n'a pas pu être envoyée (réponse %s)", rep.reponse.id)
            envoyeur.texte(dest, s.texte)
    elif vocal:
        if f := fiche(rep, envoyeur.gras):  # question vocale : la voix est partie, puis la fiche
            envoyeur.texte(dest, f)
    else:  # question écrite, ou voix indisponible ou en panne : le texte complet
        envoyeur.texte(dest, s.texte)


def _dire(dest: str, rep: AskResponse, services: Services, envoyeur: Envoyeur) -> bool:
    """Prépare ET envoie la note vocale ; False (le texte complet partira) si pas de phrase wolof, services
    absents ou une panne, y compris à l'envoi (dépôt chez Meta, sendVoice) : revue de SAN sur #146."""
    try:
        envoyeur.preparer_vocal(dest)
        note = services.parler(rep)
        if note is None:
            return False
        envoyeur.vocal(dest, note.opus)
        return True
    except Exception:  # noqa: BLE001 — une panne de la voix ne doit jamais empêcher la réponse
        _log.exception("voix : la note n'a pas pu être envoyée (réponse %s)", rep.reponse.id)
        return False
