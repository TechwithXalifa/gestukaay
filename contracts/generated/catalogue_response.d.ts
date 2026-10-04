/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */

/**
 * GET /v1/indicators?domaine=&q=&niveau=&limite=&decalage= — triés : vérifiés d'abord, puis libellé.
 */
export interface CatalogueResponse {
  version_contrat: string;
  version_socle: string;
  total: number;
  indicateurs: IndicateurResume[];
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
