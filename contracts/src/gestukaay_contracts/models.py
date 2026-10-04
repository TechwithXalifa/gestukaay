"""Contrat d'échange Gëstukaay — source de vérité unique.

Ces modèles définissent ce qui circule entre :
  - le moteur (KBD)  -> le backend (SAN)   : appel Python direct
  - le backend (SAN) -> le web (SAN)       : JSON sur HTTP (/v1/ask, ...)
  - le backend (SAN) -> les canaux (KBD)   : WhatsApp / Telegram

Le schéma JSON (generated/*.schema.json) et les types TypeScript
(generated/contract.ts) sont GÉNÉRÉS depuis ce fichier : ne jamais les
modifier à la main. Toute modification ici passe par une PR approuvée
par les deux membres de l'équipe (voir CODEOWNERS).

Références au cahier des charges v1.1 entre crochets : [EF-05], [US-03]...
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

VERSION_CONTRAT = "1.4.0"


class _Strict(BaseModel):
    # Tout champ inconnu est refusé : un champ ajouté sans mise à jour du
    # contrat fait échouer les tests des deux côtés.
    # En sortie, tous les champs sont toujours présents (même à null) : le
    # schéma « serialization » les déclare donc requis, ce qui donne au front
    # des types TypeScript sans « ? » et une union discriminée sur `issue`.
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)


# ---------------------------------------------------------------------------
# Requête structurée — sortie de la couche de compréhension (LLM) [EF-03, 10.4]
# ---------------------------------------------------------------------------

Intention = Literal["valeur", "comparaison", "classement", "hors_perimetre"]


class Periode(_Strict):
    type: Literal["annee", "trimestre", "mois", "derniere"]
    # "2023", "2024-T2", "2024-03" ; None quand type = "derniere" [EF-08]
    valeur: str | None = None
    # v1.2.0 : borne de fin pour les comparaisons temporelles (« entre 2011 et 2022 »)
    fin: str | None = None


class RequeteStructuree(_Strict):
    """Ce que le LLM a le droit de produire, et rien d'autre.

    Le LLM ne reçoit jamais de valeur numérique du socle [EF-04]. Les codes
    d'indicateurs et de zones sont validés contre le socle par le moteur :
    un code inconnu -> rejet [10.4].
    """

    intention: Intention
    indicateur: str | None = Field(None, examples=["pvswjnd"])
    zones: list[str] = Field(default_factory=list, examples=[["SN-TH"]])
    periode: Periode = Field(default_factory=lambda: Periode(type="derniere"))
    desagregation: dict[str, str] | None = Field(None, examples=[{"sexe": "Féminin"}])
    # v1.2.0 : sens du tri pour les classements (« le plus » -> desc, « le moins » -> asc)
    ordre: Literal["desc", "asc"] = "desc"
    confiance: float = Field(ge=0, le=1)


# ---------------------------------------------------------------------------
# Entrée
# ---------------------------------------------------------------------------

Langue = Literal["fr", "wo"]
Canal = Literal["web", "whatsapp", "telegram", "api"]


class AskRequest(_Strict):
    """Corps de POST /v1/ask [EF-01]."""

    question: str = Field(min_length=3, max_length=300)
    langue: Langue | Literal["auto"] = "auto"  # [EF-12] l'utilisateur peut forcer
    canal: Canal = "web"
    # Identifiant opaque de conversation, pour les questions de suivi
    # « et Kaolack ? » [EF-09]. Le backend le hache avant journalisation.
    conversation_id: str | None = None
    audio_retour: bool = False  # [EF-16] audio wolof en réponse
    # v1.1.0 — question dictée puis corrigée sur le web (décision 0004 §1) :
    # le web envoie le texte final dans `question`, et ce que /v1/transcrire
    # avait produit dans `transcription_brute`. L'écart sert à mesurer le taux
    # d'erreur de la transcription (cahier 12.1) ; il n'est pas affiché.
    source: Literal["texte", "voix"] = "texte"
    transcription_brute: str | None = Field(None, max_length=1000)


class ConfirmRequest(_Strict):
    """Corps de POST /v1/ask/{id}/confirm [EF-06, US-03, US-13]."""

    choix_id: str = Field(examples=["1"])


# ---------------------------------------------------------------------------
# Briques de la réponse [5.4]
# ---------------------------------------------------------------------------


class Source(_Strict):
    """Bloc source — obligatoire sur toute valeur, tous canaux [Engagement 01]."""

    producteur: str = Field(examples=["ANSD"])
    operation: str = Field(examples=["RGPH-5"])
    titre: str
    date_publication: date
    licence: str = Field(examples=["CC BY 4.0"])
    url: str
    # Ligne prête à afficher, identique web / WhatsApp / exports [7.1 principe 10]
    libelle: str = Field(examples=["ANSD · RGPH-5 · publié le 31 octobre 2023 · CC BY 4.0"])


class RefIndicateur(_Strict):
    code: str  # jamais affiché au public [7.1 principe 5]
    libelle: str


class RefZone(_Strict):
    code: str = Field(examples=["SN-TH"])  # ISO 3166-2 pour les régions
    libelle: str
    # v1.1.0 : « academie » = inspection d'académie (données d'éducation,
    # décision 0003). Le libellé dit « académie de Kolda », jamais « région ».
    niveau: Literal["pays", "region", "departement", "commune", "academie"]


class PeriodeResolue(_Strict):
    valeur: str = Field(examples=["2023"])
    libelle: str = Field(examples=["2023"])


class Resultat(_Strict):
    """Une valeur officielle et tout ce qu'il faut pour la citer."""

    indicateur: RefIndicateur
    zone: RefZone
    periode: PeriodeResolue
    desagregation: dict[str, str] | None = None
    valeur: float
    # Formatée par le moteur (espace fine insécable U+202F, virgule décimale)
    # pour que tous les canaux affichent exactement la même chose [7.4].
    valeur_affichee: str = Field(examples=["2 463 677"])
    unite: str = Field(examples=["habitants"])
    source: Source
    # Traçabilité : ligne du socle d'où vient la valeur [ENF-07]
    observation_id: str
    # Zone demandée à mettre en évidence (classement, comparaison) [9.8]
    mise_en_evidence: bool = False
    # v1.1.0 — décision 0002 : les projections officielles de l'ANSD sont
    # restituées, toujours étiquetées. None = non renseigné (traiter comme observée).
    nature: Literal["observee", "estimation", "projection"] | None = None
    # Pour une estimation ou une projection : sa base, à afficher dans le badge
    base_projection: str | None = Field(None, examples=["Projections démographiques 2023-2073"])


class PointGraphique(_Strict):
    x: str
    y: float
    mise_en_evidence: bool = False


class SerieGraphique(_Strict):
    nom: str
    points: list[PointGraphique]


class Graphique(_Strict):
    """Graphique web uniquement [EF-20, EF-26].

    Les données servent d'alternative textuelle [EF-28] ; le SVG est rendu
    côté serveur (Plotly) et servi par svg_url.
    """

    type: Literal["courbe", "barres_horizontales", "barres_empilees", "deciles"]
    titre: str
    unite: str
    series: list[SerieGraphique] = Field(max_length=6)  # [9.8] au-delà : regrouper
    pied: str  # source · date · gestukaay [EF-27]
    svg_url: str | None = None


class Choix(_Strict):
    """Option proposée lors d'une correspondance approchée [EF-21, US-13]."""

    id: str = Field(examples=["1"])
    libelle: str
    requete: RequeteStructuree


class Suggestion(_Strict):
    """Indicateur proche proposé lors d'un refus [EF-05, US-02]."""

    indicateur: RefIndicateur
    question_suggeree: str


# ---------------------------------------------------------------------------
# Réponse : trois issues, et seulement trois [EF-05]
# ---------------------------------------------------------------------------


class _ReponseBase(_Strict):
    id: str  # identifiant stable -> URL partageable [EF-29]
    url: str
    question: str
    langue: Langue  # langue détectée ou forcée
    transcription: str | None = None  # questions vocales [EF-15]
    requete: RequeteStructuree | None = None  # None si incompréhension totale
    version_socle: str
    cree_le: datetime
    latence_ms: int | None = None  # rempli par le backend


class ReponseExacte(_ReponseBase):
    issue: Literal["exacte"] = "exacte"
    intention: Literal["valeur", "comparaison", "classement"]
    resultats: list[Resultat] = Field(min_length=1)
    # 1 à 3 phrases générées par gabarit, jamais par génération libre [5.4]
    explication: str
    # Vrai si l'utilisateur n'a pas donné de période [US-06]
    periode_par_defaut: bool = False
    note_perimetre: str | None = None
    graphique: Graphique | None = None  # None : valeur unique [5.4]
    citation: str  # format [EF-35]
    audio_url: str | None = None


class ReponseApprochee(_ReponseBase):
    """AUCUNE valeur dans cette issue : c'est garanti par la structure même
    du modèle (extra="forbid", pas de champ resultats) [EF-06, US-03]."""

    issue: Literal["approchee"] = "approchee"
    reformulation: str
    choix: list[Choix] = Field(min_length=2, max_length=3)


class ReponseAucune(_ReponseBase):
    issue: Literal["aucune"] = "aucune"
    # hors_socle     : donnée absente -> 3 suggestions [P3]
    # projection     : prévision demandée -> renvoi projections ANSD [2.4]
    # incomprehension: question inintelligible / transcription vide [7.3]
    # non_disponible (v1.3.0) : type de question que le moteur ne sait pas encore traiter ;
    #   jamais « cette donnée n'existe pas », la donnée existe peut-être (décision 0019)
    motif: Literal["hors_socle", "projection", "incomprehension", "non_disponible"]
    message: str
    suggestions: list[Suggestion] = Field(default_factory=list, max_length=3)


Reponse = Annotated[
    ReponseExacte | ReponseApprochee | ReponseAucune,
    Field(discriminator="issue"),
]


class AskResponse(_Strict):
    """Enveloppe HTTP de toutes les routes qui renvoient une réponse."""

    version_contrat: str = VERSION_CONTRAT
    reponse: Reponse


# ---------------------------------------------------------------------------
# v1.1.0 — Transcription seule, pour corriger avant l'envoi (décision 0004 §1)
# ---------------------------------------------------------------------------


class TranscriptionResponse(_Strict):
    """Réponse de POST /v1/transcrire [EF-11, EF-15, US-09].

    Corps de la requête : multipart, champ `fichier` (WebM/OGG Opus, 60 s
    max) et champ facultatif `langue` (fr | wo | auto). L'audio n'est pas
    conservé (10.7). Le web affiche `transcription`, l'utilisateur la corrige,
    puis envoie POST /v1/ask avec source="voix".
    """

    version_contrat: str = VERSION_CONTRAT
    transcription: str  # vide si rien n'a été compris -> état « je n'ai pas bien compris » (7.3)
    langue: Langue
    duree_s: float
    confiance: float | None = Field(None, ge=0, le=1)


# ---------------------------------------------------------------------------
# v1.1.0 — « Où je me situe » (décision 0004 §2) [EF-37 à EF-41]
# ---------------------------------------------------------------------------

# Dépenses mensuelles du ménage, en FCFA, par tranches [EF-37]
# v1.3.0 (décision 0012) : au-delà de 500 000, trois tranches au lieu d'une tranche ouverte.
# « plus_500k » reste accepté pour ne rien casser, mais n'est plus proposé par le site.
TrancheDepense = Literal["moins_50k", "50k_100k", "100k_200k", "200k_350k", "350k_500k",
                         "500k_750k", "750k_1m", "plus_1m", "plus_500k"]


class SituateRequest(_Strict):
    """Corps de POST /v1/situate. RIEN n'est conservé : ni base, ni journal [EF-40, US-21]."""

    region: str = Field(examples=["SN-KD"])  # code de région du référentiel
    taille_menage: int = Field(ge=1, le=40)  # nombre exact : intervalle par personne plus étroit
    depenses_mensuelles: TrancheDepense
    # Demandé par le cahier (EF-37) mais aucune donnée publiée ne le croise
    # encore : accepté, non exploité en v1.1.0.
    niveau_instruction_chef: Literal["aucun", "primaire", "moyen", "secondaire", "superieur"] | None = None


class Intervalle(_Strict):
    minimum: float
    maximum: float | None  # None : tranche ouverte (« plus de 1 000 000 »)
    libelle: str = Field(examples=["entre 133 333 et 480 000 FCFA"])


Position = Literal["en_dessous", "autour", "au_dessus"]


class SituateResponse(_Strict):
    """Le ménage comparé aux moyennes PUBLIÉES. Aucune tranche (décile,
    quintile) : le portail n'en publie pas les seuils (décision 0004 §2)."""

    version_contrat: str = VERSION_CONTRAT
    # Calcul sur les SEULES données saisies : dépenses × 12 / taille du ménage
    depense_par_personne_an: Intervalle
    moyenne_region: Resultat  # consommation moyenne par tête de la région (FCFA/an)
    moyenne_pays: Resultat
    # au_dessus / en_dessous si tout l'intervalle est d'un côté de la moyenne, sinon autour
    position_region: Position
    position_pays: Position
    # Repères publiés : pauvreté des ménages de même taille (national), part de la
    # région dans le quintile le plus bas, accès à l'électricité de la région…
    contexte: list[Resultat] = Field(default_factory=list, max_length=6)
    # 1 à 3 phrases par gabarit + encadré « C'est quoi une moyenne ? » [EF-39]
    explication: str



# ---------------------------------------------------------------------------
# v1.4.0 — Catalogue, fiche indicateur, séries pour Explorer (décision 0023)
#   GET /v1/indicators          -> CatalogueResponse
#   GET /v1/indicators/{code}   -> FicheIndicateur
#   GET /v1/series              -> SeriesResponse
# Lecture seule, sans LLM : tout vient du référentiel des indicateurs et du socle.
# ---------------------------------------------------------------------------

NiveauZone = Literal["pays", "region", "departement", "academie"]


class IndicateurResume(_Strict):
    """Une ligne du catalogue [5.5 « Catalogue d'indicateurs »]."""

    code: str  # sert aux adresses et aux appels ; jamais affiché au public [7.1 principe 5]
    libelle: str
    domaine: str = Field(examples=["Pauvreté"])
    unite: str = Field(examples=["%"])
    producteur: str = Field(examples=["ANSD"])
    operation: str = Field(examples=["EHCVM"])
    niveaux: list[NiveauZone]  # niveaux de zone publiés
    periode_debut: str = Field(examples=["2011"])
    periode_fin: str = Field(examples=["2022"])
    verifie: bool  # relu à la main (référentiel, décision 0005)


class CatalogueResponse(_Strict):
    """GET /v1/indicators?domaine=&q=&niveau=&limite=&decalage= — triés : vérifiés d'abord, puis libellé."""

    version_contrat: str = VERSION_CONTRAT
    version_socle: str
    total: int  # nombre d'indicateurs qui répondent aux filtres (pagination)
    indicateurs: list[IndicateurResume]


class Couverture(_Strict):
    niveau: NiveauZone
    zones: int  # nombre de zones publiées à ce niveau
    periodes: list[str]  # périodes publiées, dans l'ordre


class FicheIndicateur(_Strict):
    """GET /v1/indicators/{code} [5.5 « Fiche indicateur », US-19]. 404 si le code est inconnu."""

    version_contrat: str = VERSION_CONTRAT
    version_socle: str
    indicateur: IndicateurResume
    # Citée mot pour mot du portail, jamais rédigée ; None si le portail n'en publie pas (décision 0005)
    definition: str | None = None
    methode: str | None = None
    desagregations: list[str] = Field(default_factory=list)  # dimensions publiées (sexe, milieu…)
    couverture: list[Couverture]
    note_perimetre: str | None = None
    source: Source  # jeu d'origine du portail
    citation: str  # [EF-35], à la date de consultation
    indicateurs_lies: list[RefIndicateur] = Field(default_factory=list, max_length=6)


class PointSerie(_Strict):
    periode: str = Field(examples=["2022"])
    libelle: str = Field(examples=["2022"])
    valeur: float
    valeur_affichee: str  # formatée par le moteur, comme Resultat [7.4]
    observation_id: str  # traçabilité [ENF-07]
    nature: Literal["observee", "estimation", "projection"] | None = None
    base_projection: str | None = None


class Serie(_Strict):
    zone: RefZone
    points: list[PointSerie]  # périodes publiées seulement, dans l'ordre : rien n'est interpolé
    source: Source


class SeriesResponse(_Strict):
    """GET /v1/series?indicateur=&zones=SN-DK,SN-TH&debut=&fin= [5.5 « Explorer », US-18].

    Au plus 6 zones (422 au-delà), indicateur inconnu : 404. Une zone sans aucune valeur publiée sur
    la période figure dans `absents` : signalée, jamais interpolée (maquette Explorer).
    """

    version_contrat: str = VERSION_CONTRAT
    version_socle: str
    indicateur: RefIndicateur
    unite: str
    desagregation: dict[str, str] | None = None  # modalités retenues (total par défaut)
    series: list[Serie] = Field(max_length=6)
    absents: list[str] = Field(default_factory=list)  # codes de zone sans valeur publiée
    graphique: Graphique | None = None  # courbe (plusieurs périodes) ou barres (une seule)

# ---------------------------------------------------------------------------
# Retours utilisateurs [EF-49 à EF-51]
# ---------------------------------------------------------------------------


class FeedbackRequest(_Strict):
    reponse_id: str
    type: Literal["vote", "signalement", "suggestion_indicateur"]
    vote: Literal["utile", "pas_utile"] | None = None
    motif: Literal["chiffre_faux", "mauvaise_zone", "mauvaise_comprehension", "autre"] | None = None
    commentaire: str | None = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
# Erreurs — RFC 9457 Problem Details [10.6]
# ---------------------------------------------------------------------------


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    code_incident: str | None = None  # affiché discrètement [7.3]
