/**
 * Le socle 2026.10.0 en chiffres, affiché sur l'accueil. Recopiés de son MANIFEST.json (comptes) et
 * mesurés sur ses fichiers, jamais estimés : valeurs servies, indicateurs qui ont au moins une valeur
 * (4 247, le même total que le catalogue ; le référentiel en décrit 4 282, décision 0005), producteurs
 * dont au moins une valeur est servie, zones (0003). Rien ne les synchronise : une nouvelle version du
 * socle = mettre à jour ce fichier.
 */
export const SOCLE = {
  valeurs: 644_827,
  indicateurs: 4_247,
  producteurs: 48,
  regions: 14,
  departements: 46,
} as const;
