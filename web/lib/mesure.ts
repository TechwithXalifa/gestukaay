import { pourcentage } from "./typo";

/**
 * Résultat de la mesure officielle publié sur l'accueil et la page Méthode : le taux de bonnes
 * réponses aux tests, et lui seul (décision 0036, point 8). Recopié tel quel du rapport du benchmark,
 * jamais arrondi à la main : mesure/rapports/benchmark_llm-gemini-2.5-flash.md (passe du 9/10, rapport_de_mesure.md).
 * Le détail (refus, temps de réponse, erreurs par nature) reste dans ce rapport.
 * Une nouvelle mesure = mettre à jour ce fichier seulement.
 */
export const MESURE = {
  date: "9 octobre 2026",
  // Sur les 84 questions qui appellent une réponse (exactes et approchées), en français et en wolof
  bonne: { reussies: 83, sur: 84 },
} as const;

/** « 98,8 % », formaté une seule fois pour tout le site. */
export const TAUX_BONNES = pourcentage(MESURE.bonne.reussies / MESURE.bonne.sur);
