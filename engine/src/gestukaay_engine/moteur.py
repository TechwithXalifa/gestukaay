"""Moteur réel : question -> réponse officielle sourcée (issue #17).

Branche les briques du moteur dans l'ordre validé par KBD :
  1. compréhension (#10) ; question inintelligible -> refus (#13) ;
  2. résolution (#11, #14) ; valeur trouvée -> réponse exacte (gabarits #16, graphique #14) ;
  3. sinon :
     - question d'un type que la résolution ne traite pas (`non_traite`) -> « pas encore
       disponible », JAMAIS « cette donnée n'existe pas » : la donnée existe peut-être ;
     - projection, ou lieu inconnu non rattaché (« Paris ») -> refus (#13) ;
     - sinon réponse approchée (#12) : 2 à 3 choix vérifiés ; un seul choix -> refus avec ce
       choix en suggestion ; aucun -> refus avec des indicateurs proches.
executer() (confirmation d'un choix) : résolution seule ; un échec donne un refus, jamais une
nouvelle réponse approchée (pas de boucle).

Langue : tant que la détection (#24) et les gabarits wolof (#25) manquent, la réponse est rédigée
en français et déclarée « fr », même pour une question en wolof : pas de faux wolof (décision 0009).
transcrire() n'est pas construit (#28) : NonDisponible, rendu en 503 par le backend, plutôt que le
texte fixe du faux moteur. situer() : « Où je me situe » (#95, situer.py).
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime

from gestukaay_contracts.models import (
    AskRequest,
    AskResponse,
    ReponseApprochee,
    ReponseExacte,
    RequeteStructuree,
    SituateRequest,
    SituateResponse,
    TranscriptionResponse,
)
from gestukaay_socle.zones import normaliser

from .approchee import Approchee, RepliAucune, proposer_approchee, rattachements
from .comprehension import Comprehension, Comprise
from .gabarits import citation, explication, note_perimetre
from .interface import NonDisponible
from .refus import Refus, construire_reponse_aucune, est_projection, refuser
from .resolution import Introuvable, Resolution, national, ordre_effectif, resoudre
from .situer import situer as situer_menage
from .socle import Socle, socle

LANGUE = "fr"  # seule langue de rédaction tant que #24 et #25 ne sont pas faites
URL_PROVISOIRE = "https://app.gestukaay.test/r/{id}"  # remplacée par le backend (adresse stable)

MESSAGE_NON_DISPONIBLE = "Ce type de question n'est pas encore disponible."
MOTIF_NON_DISPONIBLE = "non_disponible"  # contrat 1.3.0 (#99) : jamais « hors_socle »


def _comprehension() -> Comprehension:
    """La chaîne LLM du .env ; sans LLM_CHAINE, les règles locales seulement (signalé)."""
    if not os.environ.get("LLM_CHAINE"):
        print("[moteur] LLM_CHAINE absent : compréhension par règles locales seulement", file=sys.stderr)
        return Comprehension(None)
    from .llm import charger_client

    return Comprehension(charger_client())


class MoteurReel:
    def __init__(self, socle_: Socle | None = None, comprehension: Comprehension | None = None):
        # Chargés une fois, au démarrage du backend (socle : environ 2 s, 190 Mo)
        self.socle = socle_ if socle_ is not None else socle()
        self.comprehension = comprehension if comprehension is not None else _comprehension()

    # ------------------------------------------------------------------
    # Protocol Moteur
    # ------------------------------------------------------------------

    def repondre(self, req: AskRequest, contexte: list[RequeteStructuree | None] | None = None) -> AskResponse:
        question = req.question
        transcription = question if req.source == "voix" else None
        c = self.comprehension.comprendre(question, contexte)
        if c.incomprehensible:
            return self._aucune(refuser(self.socle, c, question, LANGUE), question, transcription)
        r = resoudre(self.socle, c.requete, LANGUE, question, c.lieux_inconnus)
        if isinstance(r, Resolution):
            return self._exacte(r, c.requete, question, transcription)
        return self._sans_valeur(r, c, question, transcription)

    def executer(self, requete: RequeteStructuree, question: str, langue: str) -> AskResponse:
        r = resoudre(self.socle, requete, LANGUE, question)
        if isinstance(r, Resolution):
            return self._exacte(r, requete, question)
        if r.raison == "non_traite":
            return self._non_disponible(requete, question)
        return self._aucune(refuser(self.socle, Comprise(requete, [], "regles"), question, LANGUE), question)

    def transcrire(self, audio: bytes, format_audio: str, langue: str = "auto") -> TranscriptionResponse:
        raise NonDisponible("transcription de la voix : pas encore disponible (#28)")

    def situer(self, req: SituateRequest) -> SituateResponse:
        return situer_menage(self.socle, req)

    def version_socle(self) -> str:
        return self.socle.version

    # ------------------------------------------------------------------
    # Construction des réponses
    # ------------------------------------------------------------------

    def _sans_valeur(self, r: Introuvable, c: Comprise, question: str, transcription: str | None) -> AskResponse:
        if r.raison == "non_traite":
            return self._non_disponible(c.requete, question, transcription)
        rats = rattachements()
        if est_projection(self.socle, c.requete, question)[0] or any(
                normaliser(lieu) not in rats for lieu in c.lieux_inconnus):
            return self._aucune(refuser(self.socle, c, question, LANGUE), question, transcription)
        a = proposer_approchee(self.socle, c.requete, r, question, LANGUE, c.lieux_inconnus)
        if isinstance(a, Approchee):
            ident = _ident()
            return AskResponse(reponse=ReponseApprochee(
                **self._base(ident, question, c.requete, transcription),
                reformulation=a.reformulation, choix=a.choix))
        if isinstance(a, RepliAucune) and a.suggestions:  # un seul choix vérifié : proposé en suggestion
            return self._aucune(Refus(a.motif, a.message, a.suggestions, c.requete), question, transcription)
        return self._aucune(refuser(self.socle, c, question, LANGUE), question, transcription)

    def _exacte(self, r: Resolution, requete: RequeteStructuree, question: str,
                transcription: str | None = None) -> AskResponse:
        ident = _ident()
        res = r.resultats
        nationaux = {x.indicateur.code: n for x in res if (n := national(self.socle, x, LANGUE))}
        intention = requete.intention if requete.intention in ("comparaison", "classement") else "valeur"
        return AskResponse(reponse=ReponseExacte(
            **self._base(ident, question, requete, transcription),
            intention=intention,
            resultats=res,
            explication=explication(res, r.defauts.get("periode", False), nationaux, intention,
                                    ordre_effectif(requete, question)),
            periode_par_defaut=r.defauts.get("periode", False),
            note_perimetre=note_perimetre(res[0]),
            graphique=r.graphique,
            citation=citation(res[0], datetime.now(UTC).date(), URL_PROVISOIRE.format(id=ident)),
        ))

    def _non_disponible(self, requete: RequeteStructuree | None, question: str,
                        transcription: str | None = None) -> AskResponse:
        refus = Refus(MOTIF_NON_DISPONIBLE, MESSAGE_NON_DISPONIBLE, [], requete)
        return self._aucune(refus, question, transcription)

    def _aucune(self, refus: Refus, question: str, transcription: str | None = None) -> AskResponse:
        ident = _ident()
        return AskResponse(reponse=construire_reponse_aucune(
            refus, question, self.socle.version, ident, URL_PROVISOIRE.format(id=ident), LANGUE,
            transcription))

    def _base(self, ident: str, question: str, requete: RequeteStructuree | None,
              transcription: str | None) -> dict:
        return {"id": ident, "url": URL_PROVISOIRE.format(id=ident), "question": question,
                "langue": LANGUE, "transcription": transcription, "requete": requete,
                "version_socle": self.socle.version, "cree_le": datetime.now(UTC)}


def _ident() -> str:
    return uuid.uuid4().hex[:12]
