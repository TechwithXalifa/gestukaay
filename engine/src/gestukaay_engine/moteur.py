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
import re
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
from .candidats import (
    capacite_au_lieu_de,
    desagregation_citee,
    deux_sexes,
    groupe_non_traduit,
    index,
    mesure_inverse,
    nature_differente,
    periode_relative,
    periodes_citees,
    ratio_non_publie,
    sans_emploi,
    sans_periode_relative,
    texte_normalise,
)
from .compagnons import compagnon
from .comprehension import (
    _TOUTES_REGIONS,
    SEUIL_REGLES,
    Comprehension,
    Comprise,
    _meme_notion,
    periode_de,
    precedente_comprise,
    sujet_dans_la_question,
)
from .conversation import domaine_demande, sans_politesse
from .conversation import texte as conversation_texte
from .gabarits import (
    citation,
    explication,
    les_autres,
    libelle_court,
    note_perimetre,
    periode_en_lettres,
)
from .interface import NoteVocale
from .langue import detecter
from .nombres import en_chiffres
from .parole import en_wolof, texte_parle
from .refus import Refus, construire_reponse_aucune, est_projection, refuser, verifier_suggestion
from .resolution import (
    ANNEE_EN_COURS,
    Introuvable,
    Resolution,
    national,
    ordre_effectif,
    resoudre,
    zone_de_la_serie,
)
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
        reste = sans_emploi(en_chiffres(sans_politesse(saisie_propre(req.question))))
        rep = self._repondre(req.model_copy(update={"question": reste}) if reste != req.question else req, contexte)
        if reste != req.question:
            rep = rep.model_copy(update={"reponse": rep.reponse.model_copy(update={"question": req.question})})
        return self._dans_la_langue(rep, langue)

    def _repondre(self, req: AskRequest, contexte: list[RequeteStructuree | None] | None = None) -> AskResponse:
        question = req.question
        transcription = question if req.source == "voix" else None
        if dom := domaine_demande(question):  # « quelles données sur l'agriculture ? » (#216) : lecture du référentiel
            return self._domaine(dom, question, transcription, req.langue if req.langue in ("fr", "wo") else detecter(question))
        rel = periode_relative(question)
        c = self.comprehension.comprendre(sans_periode_relative(question) if rel else question, contexte)
        if (c.requete and c.requete.indicateur and contexte and (prec := precedente_comprise(contexte))
                and c.requete.indicateur == prec.indicateur and groupe_non_traduit(question)):
            # #281 : « et pour les mamans ? » après la mortalité des enfants ne resert jamais la même valeur
            proches = [x for x in c.candidats if x.indicateur.code == prec.indicateur] + c.proches
            c = replace(c, requete=c.requete.model_copy(update={"indicateur": None, "intention": "hors_perimetre"}),
                        proches=proches, incomprehensible=False)  # un refus « non publié », le précédent suggéré
        if c.requete and c.requete.indicateur and rel:
            c = replace(c, requete=self._periode_relative(c.requete, rel))
        if c.requete and (propre := self._precisions_publiees(c.requete, question)) is not c.requete:
            c = replace(c, requete=propre)  # B en amont : vaut aussi pour l'approchée (« ville de Thiès »)
        if c.conversation:  # salutation, « qui es-tu », définition, « pourquoi »… : pas un refus (0033)
            langue = req.langue if req.langue in ("fr", "wo") else detecter(question)
            return self._conversation(c, question, transcription, langue)
        if c.incomprehensible:
            return self._aucune(refuser(self.socle, c, question, LANGUE), question, transcription)
        if c.requete and (dite := categorie_dite(c.requete, question)):
            c = replace(c, requete=dite)  # « véhicules particuliers » : la catégorie est dite, pas de choix
        if c.requete.indicateur and (capacite_au_lieu_de(c.requete.indicateur, question)
                                     or nature_differente(c.requete.indicateur, question)):
            # #217 : les lits d'un centre de santé ne sont pas des centres ; un candidat qui compte ce que la question
            # nomme d'abord (hfhored.centres-de-sante), sinon un refus avec suggestions (bloc suivant)
            autre = next((x.indicateur.code for x in c.candidats if x.indicateur.code != c.requete.indicateur
                          and not capacite_au_lieu_de(x.indicateur.code, question)
                          and not nature_differente(x.indicateur.code, question)
                          and sujet_dans_la_question(x.indicateur.code, question)), None)
            if autre:
                c = replace(c, requete=c.requete.model_copy(update={"indicateur": autre}))
        if c.requete.indicateur and (ratio_non_publie(c.requete.indicateur, question)
                                     or capacite_au_lieu_de(c.requete.indicateur, question)
                                     or nature_differente(c.requete.indicateur, question)
                                     or (mesure_inverse(c.requete.indicateur, question)  # une prévision d'abord
                                         and not est_projection(self.socle, c.requete, question)[0])):
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

    def _serie_de_la_zone(self, r: Introuvable, c: Comprise, question: str) -> tuple[Comprise, Resolution] | None:
        """La zone demandée n'est pas publiée par l'indicateur choisi (« riz brisé » : Dakar seulement) mais un
        autre candidat la publie, sur la même notion et dans la même unité (le prix de détail du riz par région) :
        FR-049 et WO-021 finissaient en « donnée absente » (benchmark LLM du 09/10). Jamais une autre mesure : un
        taux n'est pas remplacé par un effectif.
        Même chose pour une précision demandée que l'indicateur choisi ne publie pas (#210 : « et chez les
        jeunes ? » après le chômage trimestriel, sans âge ; le chômage annuel publie les 15-24 ans)."""
        choisi = indicateurs().get(c.requete.indicateur or "")
        zone = r.raison == "zone_non_couverte" and bool(c.requete.zones)
        precision = r.raison == "desagregation_absente" and r.dimension_absente in desagregation_citee(question)
        if not (zone or precision) or c.lieux_inconnus or choisi is None:
            return None
        unite = _unite(choisi)
        voisins = c.candidats[:5] + (index().chercher(choisi.libelle_fr.split(" — ")[0], 8) if precision else [])
        for cand in voisins:
            ind = cand.indicateur
            if ind.code == choisi.code or not unite or _unite(ind) != unite or not _meme_notion(choisi, ind):
                continue
            req = c.requete.model_copy(update={"indicateur": ind.code})
            if isinstance(r2 := resoudre(self.socle, req, LANGUE, question), Resolution):
                return replace(c, requete=req), r2
        return None

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
        if ailleurs := self._serie_de_la_zone(r, c, question):  # en dernier, avant un refus
            return self._exacte(ailleurs[1], ailleurs[0].requete, question, transcription)
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

    def _periode_relative(self, requete: RequeteStructuree, rel: str) -> RequeteStructuree:
        """#266 à #269 : la période relative lue dans la question remplace celle du LLM (« 2024-T1 » inventé pour
        « le trimestre courant ») ; elle est résolue sur la série elle-même."""
        if rel == "deux_dernieres":  # la résolution prend les deux dernières périodes publiées
            intention = requete.intention if requete.intention == "classement" else "comparaison"
            return requete.model_copy(update={"periode": Periode(type="derniere"), "intention": intention})
        z = requete.zones[0] if len(requete.zones or []) == 1 else None
        serie = sorted({o.periode for o in self.socle.observations(requete.indicateur)
                        if o.zone == zone_de_la_serie(self.socle, requete.indicateur, z)})
        if not serie:
            return requete
        return requete.model_copy(update={"periode": periode_de(serie[0]), "intention": "valeur"})

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
        if intention == "classement" and len(res) > 3 and _TOUTES_REGIONS.search(normaliser(question)):
            texte = f"{texte} {les_autres(res[3:])}"  # #217 : « dans chaque région », toutes les valeurs
        if (requete.periode.type == "derniere" and not r.defauts.get("extremum") and len(res) == 1
                and res[0].periode.valeur[:4].isdigit() and int(res[0].periode.valeur[:4]) <= ANNEE_EN_COURS - 6):
            # #282 : « combien on importe de riz » -> septembre 2017, sans le dire
            texte = (f"{texte} Attention : cette donnée date de {res[0].periode.valeur[:4]} ; "
                     "aucune valeur plus récente n'est publiée dans les jeux couverts.")
        texte = _precisions_de_lecture(texte, question, res)
        if rel := periode_relative(question):
            texte = f"{texte} {_dit_relative(rel, question, res)}".rstrip()
        if manquantes := _annees_non_servies(question, res):  # #242 : jamais une année citée perdue en silence
            texte = (f"{texte} Vous avez aussi cité {_liste(manquantes)} : une réponse porte sur deux périodes au plus, "
                     f"posez la question pour {'cette année' if len(manquantes) == 1 else 'ces années'} à part.")
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
        fiche = ("unite", "frequence", "producteur")  # #273
        sugg = (verifier_suggestion(self.socle, code, zone) if code and cle in ("definition", "pourquoi", *fiche)
                else None)
        if cle in (*fiche, "definition") and not code:  # les mots sur la fiche brouillent la recherche (#273)
            code = _sujet_de_la_fiche(question)
            sugg = verifier_suggestion(self.socle, code, zone) if code else None
        ind = indicateurs().get(code) if code else None
        if cle == "definition" and ind and ind.definition.strip():
            message = conversation_texte("definition", langue, definition=ind.definition.strip().rstrip(".") + ".")
        elif cle == "definition":
            message = conversation_texte("definition_absente" if sugg else "aide", langue)
        elif cle in fiche and ind:
            message = conversation_texte(cle, langue, **_fiche(ind))
        elif cle in fiche:
            message = conversation_texte("aide", langue)
        elif cle == "pourquoi" and not sugg:  # pas de « Voici le chiffre : » sans chiffre (revue de SAN)
            message = conversation_texte("pourquoi_sans_chiffre", langue)
        else:
            message = conversation_texte(cle, langue)
        ident = _ident()
        base = self._base(ident, question, c.requete if sugg else None, transcription) | {"langue": langue}
        return AskResponse(reponse=ReponseAucune(**base, motif="conversation", message=message,
                                                 suggestions=[sugg] if sugg else []))

    def _domaine(self, domaine: str, question: str, transcription: str | None, langue: str) -> AskResponse:
        """Jusqu'à 3 chiffres publiés du domaine, en questions à poser : vérifiés, P1 d'abord, un par jeu, résolus
        dans le socle comme toute suggestion (zéro chiffre inventé). Aucune valeur dans le message."""
        retenus, jeux = [], set()
        candidats = sorted((i for i in indicateurs().values() if i.domaine == domaine and i.verification == "verifie"),
                           key=lambda i: (i.priorite, -i.nb_valeurs))
        for ind in candidats:
            if ind.dataset_id in jeux:
                continue
            if sugg := (verifier_suggestion(self.socle, ind.code, "SN") or verifier_suggestion(self.socle, ind.code, "SN-DK")):
                retenus.append(sugg)
                jeux.add(ind.dataset_id)
            if len(retenus) == 3:  # le contrat en permet 3
                break
        message = conversation_texte("domaine" if retenus else "aide", langue, domaine=domaine)
        base = self._base(_ident(), question, None, transcription) | {"langue": langue}
        return AskResponse(reponse=ReponseAucune(**base, motif="conversation", message=message, suggestions=retenus))

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


def _unite(ind) -> str:
    """Unité comparable : « pour cent », « pourcentage » et « % » sont la même (#210)."""
    u = normaliser(ind.unite_affichee or ind.unite or "")
    return "%" if u in ("%", "pour cent", "pourcentage", "en %") else u


_BALISE = re.compile(r"</?[a-zA-Z][^<>]{0,200}>")  # #241 : « taux < 5 % et > 2 % » n'est pas une balise
_TIRET = re.compile(r"[–—]")  # #241 : « 2011–2022 » garde ses deux années
_SYMBOLE = re.compile(r"[^\w\s'’?!.,;:%()«»\"/+<>=-]")


def _annees_non_servies(question: str, res: list) -> list[str]:
    """#242 : « pauvreté à Dakar en 2011, 2019 et 2022 » ; la résolution sert deux périodes au plus."""
    citees = list(dict.fromkeys(p for p in periodes_citees(question) if re.fullmatch(r"\d{4}", p)))
    if len(citees) < 3:
        return []
    servies = {x.periode.valeur[:4] for x in res}
    return [a for a in citees if a not in servies]


def _precisions_de_lecture(texte: str, question: str, res: list) -> str:
    """Ce que la phrase pourrait faire croire, dit (test du bot du 10/10) :
    - #275 : des prix relevés dans l'agglomération de Dakar ne sont pas ceux de « la région de Dakar » ;
    - #276 : « l'écart entre » : aucun écart n'est calculé (zéro chiffre fabriqué), les deux valeurs suffisent ;
    - #276 : deux années demandées, série mensuelle : ce sont deux mois (décembre), pas deux années entières."""
    note = note_perimetre(res[0]) or ""
    if "agglomeration" in normaliser(note):
        texte = texte.replace("dans la région de Dakar", "dans l'agglomération de Dakar")
    t = texte_normalise(question)  # « l'écart » -> « l ecart » (normaliser colle l'apostrophe)
    if len(res) == 2 and re.search(r"\b(ecart|difference)\b", t):
        texte = f"{texte} Gëstukaay ne calcule pas d'écart : voici les deux valeurs publiées."
    annees = [p for p in periodes_citees(question) if re.fullmatch(r"\d{4}", p)]
    mois = [x.periode.valeur for x in res if re.fullmatch(r"\d{4}-\d{2}", x.periode.valeur)]
    if len(annees) >= 2 and len(mois) == len(res) == 2:
        texte = (f"{texte} La série est mensuelle : la comparaison porte sur deux mois "
                 f"({periode_en_lettres(mois[0])[3:]} et {periode_en_lettres(mois[1])[3:]}), pas sur la moyenne de l'année.")
    return texte


_MOTS_DE_LA_FICHE = re.compile(
    r"\b(quelle|quel|quelles|en|dans|est|sont|unite|utilisee|utilise|de|mesure|mesurer|pour|a|frequence|les|des|la|le|"
    r"l|donnees|indicateur|elles|ils|mises?|jour|qui|produit|publie|ou|calcule|fournit|collecte|signifie|"
    r"que|se|en quoi|quoi|tous|combien|signifient|veut|dire|c|definition)\b")


def _sujet_de_la_fiche(question: str) -> str | None:
    """« Quelle unité est utilisée pour mesurer le taux de chômage ? » -> l'indicateur cherché sur « taux chômage »."""
    reste = re.sub(r"\s+", " ", _MOTS_DE_LA_FICHE.sub(" ", texte_normalise(question))).strip()
    if not reste:
        return None
    meilleurs = index().chercher(reste, 5)
    return meilleurs[0].indicateur.code if meilleurs and meilleurs[0].score >= SEUIL_REGLES else None


_FREQUENCES = {"A": "chaque année", "M": "chaque mois", "T": "chaque trimestre", "Q": "chaque trimestre",
               "S": "chaque semestre", "J": "chaque jour", "H": "chaque semaine"}


def _fiche(ind) -> dict[str, str]:
    """#273 : unité, fréquence, période couverte et producteur d'un indicateur, lus dans le référentiel."""
    from gestukaay_socle.indicateurs import nom_du_jeu
    unite = (ind.unite_affichee or ind.unite or "").strip()
    return {"libelle": libelle_court(ind),
            "unite": unite or "une unité que la source ne précise pas",
            "frequence": _FREQUENCES.get((ind.frequence or "").strip().upper()[:1], "à intervalles irréguliers"),
            "debut": str(ind.periode_debut or "?"), "fin": str(ind.periode_fin or "?"),
            "producteur": _producteur_lisible(ind.producteur or "l'ANSD"), "jeu": nom_du_jeu(ind.jeu)}


def _producteur_lisible(p: str) -> str:
    """« Direction-de-l-Administration-Penitentiaire-Ministere » -> « Direction de l'Administration Penitentiaire
    Ministere » (même remise en clair que les sources, resolution.producteur_et_operation)."""
    p = p.strip()
    if "-" in p and " " not in p:
        p = re.sub(r"\b([ldLD]) ", r"\1'", p.replace("-", " "))
    return p


def _dit_relative(rel: str, question: str, res: list) -> str:
    """Ce qui est servi pour une période relative, et la fréquence de la série si elle n'est pas celle demandée."""
    if rel == "debut":
        return "C'est la première période publiée de la série."
    servies = [x.periode.valeur for x in res]
    t = normaliser(question)
    frequence = ("trimestrielle" if any("-T" in p for p in servies) else
                 "mensuelle" if any(re.fullmatch(r"\d{4}-\d{2}", p) for p in servies) else "annuelle")
    demandee = ("trimestrielle" if "trimestre" in t else "mensuelle" if re.search(r"\bmois\b", t) else
                "annuelle" if re.search(r"\b(annee|an)\b", t) else frequence)
    phrase = "Ce sont les deux dernières périodes publiées."
    if demandee != frequence:
        phrase = f"La série est {frequence} : ce sont ses deux dernières périodes publiées."
    return phrase


def _liste(annees: list[str]) -> str:
    return annees[0] if len(annees) == 1 else f"{', '.join(annees[:-1])} et {annees[-1]}"


def saisie_propre(question: str) -> str:
    """Recette du 09/10 (#204) : « 😀 Combien d'habitants à Thiès ? 🙏 », des espaces en trop ou une balise
    HTML faisaient refuser une question comprise (« Combien », qui n'ouvrait plus le texte, passait pour un
    lieu). Balises, emojis et symboles retirés, espaces réduits ; la réponse garde la question telle que posée."""
    return re.sub(r"\s+", " ", _SYMBOLE.sub(" ", _TIRET.sub("-", _BALISE.sub(" ", question)))).strip()


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
