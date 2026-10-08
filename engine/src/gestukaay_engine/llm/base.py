"""Types communs du client LLM multi-fournisseur (issue #9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Fournisseur = Literal["openai_compatible", "huggingface", "anthropic", "gemini", "regles"]
# Comment demander du JSON au fournisseur. Dans tous les cas, la réponse est
# revalidée chez nous avec le schéma Pydantic (EF-03).
ModeJson = Literal["schema", "objet", "aucun"]


@dataclass(frozen=True)
class Maillon:
    """Un fournisseur + un modèle, essayé à son tour dans la chaîne."""

    nom: str  # principal, repli, secours…
    fournisseur: Fournisseur
    modele: str = ""
    cle: str = ""
    url: str = ""  # vide : URL officielle du fournisseur
    delai_s: float = 2.0  # cahier 10.4 : échéance réelle, le maillon est abandonné au-delà
    # Relais (recette du 08/10) : au bout de relais_s sans réponse, le maillon SUIVANT part en parallèle ;
    # la réponse de celui-ci reste préférée s'il répond avant son délai. None : pas de relais (séquentiel).
    relais_s: float | None = None
    temperature: float | None = 0.0  # None : ne pas l'envoyer (certains modèles la refusent)
    mode_json: ModeJson | None = None  # None : le meilleur mode connu du fournisseur
    prix_entree: float | None = None  # $ par million de jetons, si le fournisseur ne donne pas le coût
    prix_sortie: float | None = None
    # OpenRouter seulement : hébergeurs à essayer dans l'ordre (« cerebras », « groq »…)
    # et tri des autres (« latency », « throughput », « price »).
    hebergeurs: tuple[str, ...] = ()
    tri: str | None = None
    # OpenRouter et Gemini direct : raisonnement des modèles qui « réfléchissent » avant de
    # répondre (gpt-oss, DeepSeek, Qwen3…). « non » le désactive ; sinon minimal,
    # low, medium, high. None : réglage par défaut du modèle (souvent lent).
    raisonnement: str | None = None


@dataclass(frozen=True)
class Brut:
    """Ce qu'un adaptateur renvoie : le texte et la comptabilité de l'appel."""

    texte: str
    jetons_entree: int | None = None
    jetons_sortie: int | None = None
    cout_usd: float | None = None
    modele: str = ""


@dataclass(frozen=True)
class Tentative:
    maillon: str
    fournisseur: str
    modele: str
    # abandon : un maillon préféré a répondu pendant qu'il travaillait encore (relais)
    statut: Literal["ok", "delai", "reseau", "http", "refus", "json", "schema", "indisponible", "abandon"]
    latence_ms: int
    detail: str = ""


@dataclass
class Appel:
    """Bilan d'un appel complet, pour le journal des requêtes (cahier 10.9)."""

    tentatives: list[Tentative] = field(default_factory=list)
    maillon: str = ""
    fournisseur: str = ""
    modele: str = ""
    latence_ms: int = 0  # durée réelle de l'appel (les maillons en relais se chevauchent)
    jetons_entree: int | None = None
    jetons_sortie: int | None = None
    cout_usd: float | None = None


class EchecLLM(Exception):
    """Aucun maillon n'a produit de réponse valide : le moteur répond « incompréhension »."""

    def __init__(self, appel: Appel):
        self.appel = appel
        resume = " ; ".join(f"{t.maillon}={t.statut}" for t in appel.tentatives)
        super().__init__(f"aucune réponse valide ({resume})")


class ErreurAdaptateur(Exception):
    """Échec d'un maillon, avec la catégorie qui ira dans Tentative.statut."""

    def __init__(self, statut: str, detail: str = ""):
        self.statut = statut
        super().__init__(detail)
