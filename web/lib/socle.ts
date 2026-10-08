/**
 * Le socle servi en chiffres, affiché sur l'accueil et dans le pied de page. Recopiés des décisions
 * qui les mesurent, jamais estimés : 0008 (valeurs servies), 0005 (indicateurs du référentiel),
 * 0002 (producteurs du portail), 0003 (zones). Une nouvelle version du socle = mettre à jour ce fichier.
 */
export const SOCLE = {
  version: "2026.10.0",
  valeurs: 644_827,
  indicateurs: 4_282,
  producteurs: 48,
  regions: 14,
  departements: 46,
} as const;
