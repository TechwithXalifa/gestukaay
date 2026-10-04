/**
 * Résultats de la mesure officielle affichés sur la page Méthode (cahier 12.1 : « nous publions nos
 * erreurs avec nos réussites »). Recopiés tels quels du rapport du benchmark, jamais arrondis à la
 * main : mesure/rapports/benchmark_llm-google-gemini-2.5-flash.md (PR #115, KBD).
 * Une nouvelle mesure = mettre à jour ce fichier seulement.
 */
export const MESURE = {
  date: "4 octobre 2026",
  questions: { total: 103, fr: 72, wo: 31 },
  // Exactitude : sur les 83 questions qui appellent une réponse (exactes et approchées)
  bonne: { reussies: 74, sur: 83 },
  // Refus pertinents : sur les 20 questions dont la bonne réponse est un refus
  refus: { reussis: 20, sur: 20 },
  latence: { medianeMs: 1393, p95Ms: 1996 },
  inventes: 0, // invariant « zéro chiffre inventé » : 0 violation
  // Toutes questions confondues, par langue de la question (écrite)
  langues: { fr: { reussies: 67, sur: 72 }, wo: { reussies: 27, sur: 31 } },
  // Les 9 questions non conformes, regroupées par nature
  erreurs: { approcheesEnRefus: 5, horsSujet: 2, sansReponse: 2 },
} as const;
