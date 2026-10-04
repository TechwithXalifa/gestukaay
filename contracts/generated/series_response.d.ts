/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */

/**
 * GET /v1/series?indicateur=&zones=SN-DK,SN-TH&debut=&fin= [5.5 « Explorer », US-18].
 *
 * Au plus 6 zones (422 au-delà), indicateur inconnu : 404. Une zone sans aucune valeur publiée sur
 * la période figure dans `absents` : signalée, jamais interpolée (maquette Explorer).
 */
export interface SeriesResponse {
  version_contrat: string;
  version_socle: string;
  indicateur: RefIndicateur;
  unite: string;
  desagregation: {
    [k: string]: string;
  } | null;
  /**
   * @maxItems 6
   */
  series:
    | []
    | [Serie]
    | [Serie, Serie]
    | [Serie, Serie, Serie]
    | [Serie, Serie, Serie, Serie]
    | [Serie, Serie, Serie, Serie, Serie]
    | [Serie, Serie, Serie, Serie, Serie, Serie];
  absents: string[];
  graphique: Graphique | null;
}
export interface RefIndicateur {
  code: string;
  libelle: string;
}
export interface Serie {
  zone: RefZone;
  points: PointSerie[];
  source: Source;
}
export interface RefZone {
  code: string;
  libelle: string;
  niveau: "pays" | "region" | "departement" | "commune" | "academie";
}
export interface PointSerie {
  periode: string;
  libelle: string;
  valeur: number;
  valeur_affichee: string;
  observation_id: string;
  nature: ("observee" | "estimation" | "projection") | null;
  base_projection: string | null;
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
