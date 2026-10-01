/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */

/**
 * Le ménage comparé aux moyennes PUBLIÉES. Aucune tranche (décile,
 * quintile) : le portail n'en publie pas les seuils (décision 0004 §2).
 */
export interface SituateResponse {
  version_contrat: string;
  depense_par_personne_an: Intervalle;
  moyenne_region: Resultat;
  moyenne_pays: Resultat;
  position_region: "en_dessous" | "autour" | "au_dessus";
  position_pays: "en_dessous" | "autour" | "au_dessus";
  /**
   * @maxItems 6
   */
  contexte:
    | []
    | [Resultat]
    | [Resultat, Resultat]
    | [Resultat, Resultat, Resultat]
    | [Resultat, Resultat, Resultat, Resultat]
    | [Resultat, Resultat, Resultat, Resultat, Resultat]
    | [Resultat, Resultat, Resultat, Resultat, Resultat, Resultat];
  explication: string;
}
export interface Intervalle {
  minimum: number;
  maximum: number | null;
  libelle: string;
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
