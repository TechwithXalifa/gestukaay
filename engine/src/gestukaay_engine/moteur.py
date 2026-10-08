"""Moteur réel : question -> réponse officielle sourcée (issue #17).

Branche les briques du moteur dans l'ordre validé par KBD :
  1. compréhension (#10) ; question inintelligible -> refus (#13) ;
  2. modalité ambiguë citée (« voitures », rattachements.csv) -> réponse approchée d'emblée, même si
     le total existe : « voitures » n'est pas le parc total (#116, choix KBD) ;
  3. résolution (#11, #14) ; valeur trouvée -> réponse exacte (gabarits #16, graphique #14) ;
  4. sinon :
     - question d'un type que la résolution ne traite pas (`non_traite`) -> « pas encore
       disponible », JAMAIS « cette donnée n'existe pas » : la donnée existe peut-être ;
     - projection, ou lieu inconnu non rattaché (« Paris ») -> refus (#13) ;
     - sinon réponse approchée (#12) : 2 à 3 choix vérifiés ; un seul choix -> refus avec ce
       choix en suggestion ; aucun -> refus avec des indicateurs proches.
executer() (confirmation d'un choix) : résolution seule ; un échec donne un refus, jamais une
nouvelle réponse approchée (pas de boucle).

Langue : tant que la détection (#24) et les gabarits wolof (#25) manquent, la réponse est rédigée
en français et déclarée « fr », même pour une question en wolof : pas de faux wolof (décision 0009).
transcrire() : service M-Kiriku, repli ADIA, nombres en chiffres (#28, transcription.py) ; si rien ne
répond, NonDisponible (503 côté backend). situer() : « Où je me situe » (#95, situer.py).
"""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import replace
from datetime import UTC, datetime

from gestukaay_contracts.models import (
    AskRequest,
    AskResponse,
    CatalogueResponse,
    FicheIndicateur,
    Periode,
    ReponseApprochee,
    ReponseAucune,
    ReponseExacte,
    RequeteStructuree,
    SeriesResponse,
    SituateRequest,
    SituateResponse,
    TranscriptionResponse,
)
from gestukaay_socle.indicateurs import indicateurs
from gestukaay_socle.zones import normaliser

from . import donnees
from .approchee import (
    Approchee,
    RepliAucune,
    categorie_dite,
    indicateur_ambigu,
    modalite_citee,
    proposer_approchee,
    rattachements,
)
from .candidats import desagregation_citee, deux_sexes, ratio_non_publie
from .compagnons import compagnon
from .comprehension import Comprehension, Comprise
from .conversation import sans_politesse
from .conversation import texte as conversation_texte
from .gabarits import citation, explication, note_perimetre
from .interface import NoteVocale
from .langue import detecter
from .nombres import en_chiffres
from .parole import en_wolof, texte_parle
from .refus import Refus, construire_reponse_aucune, est_projection, refuser, verifier_suggestion
from .resolution import Introuvable, Resolution, national, ordre_effectif, resoudre
from .situer import situer as situer_menage
from .socle import Socle, socle
from .synthese import Synthetiseur
from .transcription import Transcripteur

LANGUE = "fr"  # langue de rédaction des gabarits ; la réponse wolof est réécrite ensuite (0032)
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
    def __init__(self, socle_: Socle | None = None, comprehension: Comprehension | None = None,
                 transcripteur: Transcripteur | None = None, synthetiseur: Synthetiseur | None = None):
        # Chargés une fois, au démarrage du backend (socle : environ 2 s, 190 Mo)
        self.socle = socle_ if socle_ is not None else socle()
        self.comprehension = comprehension if comprehension is not None else _comprehension()
        self.transcripteur = transcripteur or Transcripteur()  # aucun appel réseau avant une note
        self.synthetiseur = synthetiseur or Synthetiseur(transcripteur=self.transcripteur)

    # ------------------------------------------------------------------
    # Protocol Moteur
    # ------------------------------------------------------------------

    def repondre(self, req: AskRequest, contexte: list[RequeteStructuree | None] | None = None) -> AskResponse:
        # langue de la réponse (#24, 0032) : celle choisie par l'utilisateur, sinon celle de la question
        langue = req.langue if req.langue in ("fr", "wo") else detecter(req.question)
        # « Bonjour, combien d'habitants à Thiès ? » : la politesse de tête est retirée avant la compréhension
        # (0033, revue de SAN) ; la réponse garde la question telle que posée. Les nombres en lettres deviennent
        # des chiffres, comme pour une note vocale (0027) : « ci ñaari junni ak ñaar-fukk ak ñett » = 2023 (#22)
        reste = en_chiffres(sans_politesse(req.question))
        rep = self._repondre(req.model_copy(update={"question": reste}) if reste != req.question else req, contexte)
        if reste != req.question:
            rep = rep.model_copy(update={"reponse": rep.reponse.model_copy(update={"question": req.question})})
        return self._dans_la_langue(rep, langue)

    def _repondre(self, req: AskRequest, contexte: list[RequeteStructuree | None] | None = None) -> AskResponse:
        question = req.question
        transcription = question if req.source == "voix" else None
        c = self.comprehension.comprendre(question, contexte)
        if c.requete and (propre := self._precisions_publiees(c.requete, question)) is not c.requete:
            c = replace(c, requete=propre)  # B en amont : vaut aussi pour l'approchée (« ville de Thiès »)
        if c.conversation:  # salutation, « qui es-tu », définition, « pourquoi »… : pas un refus (0033)
            langue = req.langue if req.langue in ("fr", "wo") else detecter(question)
            return self._conversation(c, question, transcription, langue)
        if c.incomprehensible:
            return self._aucune(refuser(self.socle, c, question, LANGUE), question, transcription)
        if c.requete and (dite := categorie_dite(c.requete, question)):
            c = replace(c, requete=dite)  # « véhicules particuliers » : la catégorie est dite, pas de choix
        if c.requete.indicateur and ratio_non_publie(c.requete.indicateur, question):
            # « médecins pour 10 000 habitants » donnait le nombre de médecins (recette du 08/10) : on ne calcule
            # jamais un ratio, l'indicateur brut est proposé en suggestion
            proches = [x for x in c.candidats if x.indicateur.code == c.requete.indicateur] + c.proches
            sans = replace(c, requete=c.requete.model_copy(update={"indicateur": None, "intention": "hors_perimetre"}),
                           proches=proches)
            return self._aucune(refuser(self.socle, sans, question, LANGUE), question, transcription)
        if c.requete.indicateur and deux_sexes(question):
            # « entre hommes et femmes » donnait les femmes seules (recette du 08/10) : pas encore servi, on le dit
            return self._non_disponible(c.requete, question, transcription)
        if not c.lieux_inconnus and (modalite_citee(c.requete, question) or indicateur_ambigu(c.requete, question)):
            a = proposer_approchee(self.socle, c.requete, None, question, LANGUE)
            if isinstance(a, Approchee):
                return self._approchee(a, c.requete, question, transcription)
        r = resoudre(self.socle, c.requete, LANGUE, question, c.lieux_inconnus)
        if isinstance(r, Introuvable) and (sans := _sans_precision_inventee(r, c.requete, question)):
            r2 = resoudre(self.socle, sans, LANGUE, question, c.lieux_inconnus)
            if isinstance(r2, Resolution):
                c, r = replace(c, requete=sans), r2
        if isinstance(r, Resolution):
            return self._exacte(r, c.requete, question, transcription)
        return self._sans_valeur(r, c, question, transcription)

    def executer(self, requete: RequeteStructuree, question: str, langue: str) -> AskResponse:
        return self._dans_la_langue(self._executer(requete, question), langue)

    def _dans_la_langue(self, rep: AskResponse, langue: str) -> AskResponse:
        """Option B de KBD : une question en wolof reçoit sa réponse écrite en wolof (phrases de KBD)."""
        return en_wolof(rep, self.socle) if langue == "wo" else rep

    def _executer(self, requete: RequeteStructuree, question: str) -> AskResponse:
        r = resoudre(self.socle, requete, LANGUE, question)
        if isinstance(r, Resolution):
            return self._exacte(r, requete, question)
        if r.raison == "non_traite":
            return self._non_disponible(requete, question)
        if r.raison == "desagregation_ambigue":  # choix confirmé, catégorie encore à préciser : on la demande
            a = proposer_approchee(self.socle, requete, r, question, LANGUE)
            if isinstance(a, Approchee):
                return self._approchee(a, requete, question, None)
        return self._aucune(refuser(self.socle, Comprise(requete, [], "regles"), question, LANGUE), question)

    def transcrire(self, audio: bytes, format_audio: str, langue: str = "auto") -> TranscriptionResponse:
        return self.transcripteur.transcrire(audio, format_audio, langue)

    def situer(self, req: SituateRequest) -> SituateResponse:
        return situer_menage(self.socle, req)

    def parler(self, rep: AskResponse) -> NoteVocale | None:
        """Texte wolof composé (parole.py), puis voix (synthese.py) ; None : le texte part seul."""
        texte = texte_parle(rep, self.socle)
        note = self.synthetiseur.parler(texte) if texte else None
        return replace(note, texte=texte) if note else None

    # Catalogue, fiche et séries (décision 0023, #156) : lecture seule du référentiel et du socle (donnees.py)
    def catalogue(self, domaine=None, q=None, niveau=None, limite=50, decalage=0) -> CatalogueResponse:
        return donnees.catalogue(self.socle, domaine, q, niveau, limite, decalage)

    def fiche(self, code: str) -> FicheIndicateur:
        return donnees.fiche(self.socle, code)

    def series(self, indicateur: str, zones: list[str], debut=None, fin=None) -> SeriesResponse:
        return donnees.series(self.socle, indicateur, zones, debut, fin)

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
            return self._approchee(a, c.requete, question, transcription)
        if isinstance(a, RepliAucune) and a.suggestions:  # un seul choix vérifié : proposé en suggestion
            return self._aucune(Refus(a.motif, a.message, a.suggestions, c.requete), question, transcription)
        return self._aucune(refuser(self.socle, c, question, LANGUE), question, transcription)

    def _precisions_publiees(self, requete: RequeteStructuree, question: str) -> RequeteStructuree:
        """B (0034), en amont de toute résolution : une précision du LLM que la question ne cite pas (règles) et
        dont le jeu ne publie pas la dimension est retirée. Essai réel du 07/10 : « ville de Thiès » -> le LLM
        ajoutait milieu = urbain, que le recensement ne publie pas, et l'approchée finissait en refus."""
        desag = dict(requete.desagregation or {})
        if not requete.indicateur or not desag:
            return requete
        citees = desagregation_citee(question)
        for cle, valeur in list(desag.items()):
            if cle in citees:
                continue
            essai = requete.model_copy(update={"zones": ["SN"], "periode": Periode(type="derniere"),
                                               "desagregation": {cle: valeur}, "intention": "valeur"})
            r = resoudre(self.socle, essai, LANGUE)
            if isinstance(r, Introuvable) and r.dimension_absente == cle:
                desag.pop(cle)
        if len(desag) == len(requete.desagregation or {}):
            return requete
        return requete.model_copy(update={"desagregation": desag or None})

    def _approchee(self, a: Approchee, requete: RequeteStructuree, question: str,
                   transcription: str | None) -> AskResponse:
        ident = _ident()
        return AskResponse(reponse=ReponseApprochee(
            **self._base(ident, question, requete, transcription),
            reformulation=a.reformulation, choix=a.choix))

    def _exacte(self, r: Resolution, requete: RequeteStructuree, question: str,
                transcription: str | None = None) -> AskResponse:
        ident = _ident()
        res = r.resultats
        nationaux = {x.indicateur.code: n for x in res if (n := national(self.socle, x, LANGUE))}
        intention = requete.intention if requete.intention in ("comparaison", "classement") else "valeur"
        texte = explication(res, r.defauts.get("periode", False), nationaux, intention,
                            ordre_effectif(requete, question))
        an = requete.periode.valeur if requete.periode.type == "annee" else None
        if sens := r.defauts.get("extremum"):
            niveau = "le plus bas" if sens == "min" else "le plus élevé"
            texte = (f"C'est le niveau {niveau} publié entre {r.defauts['debut']} et {r.defauts['fin']}. "
                     + texte.replace(", dernière donnée publiée", ""))
        elif an and len(res) == 1 and res[0].periode.valeur.startswith(an + "-"):
            # « le riz en 2019 », « les visiteurs en 2018 » sur une série mensuelle : le mois servi est dit, et qu'aucun
            # total ni moyenne de l'année n'est calculé (zéro chiffre fabriqué)
            texte = (f"{texte} L'ANSD publie cette série par {'trimestre' if '-T' in res[0].periode.valeur else 'mois'}"
                     f" : voici la dernière période publiée de {an}, pas un total ni une moyenne de l'année.")
        if intention == "valeur" and len(res) == 1 and (c := compagnon(self.socle, res[0], LANGUE)):
            res = [*res, c[0]]  # le taux après le nombre, au même point (0024)
            texte = f"{texte} {c[1]}"
        return AskResponse(reponse=ReponseExacte(
            **self._base(ident, question, requete, transcription),
            intention=intention,
            resultats=res,
            explication=texte,
            periode_par_defaut=bool(r.defauts.get("periode", False)) and not r.defauts.get("extremum"),
            note_perimetre=note_perimetre(res[0]),
            graphique=r.graphique,
            citation=citation(res[0], datetime.now(UTC).date(), URL_PROVISOIRE.format(id=ident)),
        ))

    def _conversation(self, c: Comprise, question: str, transcription: str | None, langue: str) -> AskResponse:
        """Réponse fixe de KBD (conversation.csv) ; la définition vient du socle ; « définition » et
        « pourquoi » proposent le chiffre lié, vérifié par la résolution (zéro chiffre inventé)."""
        cle, code = c.conversation, c.requete.indicateur if c.requete else None
        zone = c.requete.zones[0] if c.requete and c.requete.zones else "SN"
        sugg = verifier_suggestion(self.socle, code, zone) if code and cle in ("definition", "pourquoi") else None
        ind = indicateurs().get(code) if code else None
        if cle == "definition" and ind and ind.definition.strip():
            message = conversation_texte("definition", langue, definition=ind.definition.strip().rstrip(".") + ".")
        elif cle == "definition":
            message = conversation_texte("definition_absente" if sugg else "aide", langue)
        elif cle == "pourquoi" and not sugg:  # pas de « Voici le chiffre : » sans chiffre (revue de SAN)
            message = conversation_texte("pourquoi_sans_chiffre", langue)
        else:
            message = conversation_texte(cle, langue)
        ident = _ident()
        base = self._base(ident, question, c.requete if sugg else None, transcription) | {"langue": langue}
        return AskResponse(reponse=ReponseAucune(**base, motif="conversation", message=message,
                                                 suggestions=[sugg] if sugg else []))

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


def _sans_precision_inventee(r: Introuvable, requete: RequeteStructuree, question: str) -> RequeteStructuree | None:
    """B (passe du 07/10) : le LLM ajoute parfois une précision que la question ne contient pas (« femmes »
    sur la vaccination des enfants). Si elle n'est pas citée (règles) ET que le jeu ne publie pas cette
    dimension du tout, on la retire. Citée par l'utilisateur, elle reste stricte (décision 0011)."""
    cle = r.dimension_absente  # posé par la résolution, pas lu dans le message (revue de SAN)
    if r.raison != "desagregation_absente" or not cle:
        return None
    desag = dict(requete.desagregation or {})
    if cle not in desag or cle in desagregation_citee(question):
        return None
    desag.pop(cle)
    return requete.model_copy(update={"desagregation": desag or None})


def _ident() -> str:
    return uuid.uuid4().hex[:12]
