/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */

/**
 * GET /v1/indicators/{code} [5.5 « Fiche indicateur », US-19]. 404 si le code est inconnu.
 */
export interface FicheIndicateur {
  version_contrat: string;
  version_socle: string;
  indicateur: IndicateurResume;
  definition: string | null;
  methode: string | null;
  desagregations: string[];
  couverture: Couverture[];
  note_perimetre: string | null;
  source: Source;
  citation: string;
  /**
   * @maxItems 6
   */
  indicateurs_lies:
    | []
    | [RefIndicateur]
    | [RefIndicateur, RefIndicateur]
    | [RefIndicateur, RefIndicateur, RefIndicateur]
    | [RefIndicateur, RefIndicateur, RefIndicateur, RefIndicateur]
    | [RefIndicateur, RefIndicateur, RefIndicateur, RefIndicateur, RefIndicateur]
    | [RefIndicateur, RefIndicateur, RefIndicateur, RefIndicateur, RefIndicateur, RefIndicateur];
}
/**
 * Une ligne du catalogue [5.5 « Catalogue d'indicateurs »].
 */
export interface IndicateurResume {
  code: string;
  libelle: string;
  domaine: string;
  unite: string;
  producteur: string;
  operation: string;
  niveaux: ("pays" | "region" | "departement" | "academie")[];
  periode_debut: string;
  periode_fin: string;
  verifie: boolean;
}
export interface Couverture {
  niveau: "pays" | "region" | "departement" | "academie";
  zones: number;
  periodes: string[];
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
export interface RefIndicateur {
  code: string;
  libelle: string;
}
