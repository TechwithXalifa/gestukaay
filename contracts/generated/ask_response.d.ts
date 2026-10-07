/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */

/**
 * Enveloppe HTTP de toutes les routes qui renvoient une réponse.
 */
export interface AskResponse {
  version_contrat: string;
  reponse: ReponseExacte | ReponseApprochee | ReponseAucune;
}
export interface ReponseExacte {
  id: string;
  url: string;
  question: string;
  langue: "fr" | "wo";
  transcription: string | null;
  requete: RequeteStructuree | null;
  version_socle: string;
  cree_le: string;
  latence_ms: number | null;
  issue: "exacte";
  intention: "valeur" | "comparaison" | "classement";
  /**
   * @minItems 1
   */
  resultats: [Resultat, ...Resultat[]];
  explication: string;
  periode_par_defaut: boolean;
  note_perimetre: string | null;
  graphique: Graphique | null;
  citation: string;
  audio_url: string | null;
}
/**
 * Ce que le LLM a le droit de produire, et rien d'autre.
 *
 * Le LLM ne reçoit jamais de valeur numérique du socle [EF-04]. Les codes
 * d'indicateurs et de zones sont validés contre le socle par le moteur :
 * un code inconnu -> rejet [10.4].
 */
export interface RequeteStructuree {
  intention: "valeur" | "comparaison" | "classement" | "hors_perimetre";
  indicateur: string | null;
  zones: string[];
  periode: Periode;
  desagregation: {
    [k: string]: string;
  } | null;
  ordre: "desc" | "asc";
  confiance: number;
}
export interface Periode {
  type: "annee" | "trimestre" | "mois" | "derniere";
  valeur: string | null;
  fin: string | null;
}
/**
 * Une valeur officielle et tout ce qu'il faut pour la citer.
 */
export interface Resultat {
  indicateur: RefIndicateur;
  zone: RefZone;
  periode: PeriodeResolue;
  desagregation: {
    [k: string]: string;
  } | null;
  valeur: number;
  valeur_affichee: string;
  unite: string;
  source: Source;
  observation_id: string;
  mise_en_evidence: boolean;
  nature: ("observee" | "estimation" | "projection") | null;
  base_projection: string | null;
}
export interface RefIndicateur {
  code: string;
  libelle: string;
}
export interface RefZone {
  code: string;
  libelle: string;
  niveau: "pays" | "region" | "departement" | "commune" | "academie";
}
export interface PeriodeResolue {
  valeur: string;
  libelle: string;
}
/**
 * Bloc source — obligatoire sur toute valeur, tous canaux [Engagement 01].
 */
export interface Source {
  producteur: string;
  operation: string;
  titre: string;
  date_publication: string;
  licence: string;
  url: string;
  libelle: string;
}
/**
 * Graphique web uniquement [EF-20, EF-26].
 *
 * Les données servent d'alternative textuelle [EF-28] ; le SVG est rendu
 * côté serveur (Plotly) et servi par svg_url.
 */
export interface Graphique {
  type: "courbe" | "barres_horizontales" | "barres_empilees" | "deciles";
  titre: string;
  unite: string;
  /**
   * @maxItems 6
   */
  series:
    | []
    | [SerieGraphique]
    | [SerieGraphique, SerieGraphique]
    | [SerieGraphique, SerieGraphique, SerieGraphique]
    | [SerieGraphique, SerieGraphique, SerieGraphique, SerieGraphique]
    | [SerieGraphique, SerieGraphique, SerieGraphique, SerieGraphique, SerieGraphique]
    | [SerieGraphique, SerieGraphique, SerieGraphique, SerieGraphique, SerieGraphique, SerieGraphique];
  pied: string;
  svg_url: string | null;
}
export interface SerieGraphique {
  nom: string;
  points: PointGraphique[];
}
export interface PointGraphique {
  x: string;
  y: number;
  mise_en_evidence: boolean;
}
/**
 * AUCUNE valeur dans cette issue : c'est garanti par la structure même
 * du modèle (extra="forbid", pas de champ resultats) [EF-06, US-03].
 */
export interface ReponseApprochee {
  id: string;
  url: string;
  question: string;
  langue: "fr" | "wo";
  transcription: string | null;
  requete: RequeteStructuree | null;
  version_socle: string;
  cree_le: string;
  latence_ms: number | null;
  issue: "approchee";
  reformulation: string;
  /**
   * @minItems 2
   * @maxItems 3
   */
  choix: [Choix, Choix] | [Choix, Choix, Choix];
}
/**
 * Option proposée lors d'une correspondance approchée [EF-21, US-13].
 */
export interface Choix {
  id: string;
  libelle: string;
  requete: RequeteStructuree;
}
export interface ReponseAucune {
  id: string;
  url: string;
  question: string;
  langue: "fr" | "wo";
  transcription: string | null;
  requete: RequeteStructuree | null;
  version_socle: string;
  cree_le: string;
  latence_ms: number | null;
  issue: "aucune";
  motif: "hors_socle" | "projection" | "incomprehension" | "non_disponible" | "conversation";
  message: string;
  /**
   * @maxItems 3
   */
  suggestions: [] | [Suggestion] | [Suggestion, Suggestion] | [Suggestion, Suggestion, Suggestion];
}
/**
 * Indicateur proche proposé lors d'un refus [EF-05, US-02].
 */
export interface Suggestion {
  indicateur: RefIndicateur;
  question_suggeree: string;
}
