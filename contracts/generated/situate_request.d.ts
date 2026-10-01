/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */

/**
 * Corps de POST /v1/situate. RIEN n'est conservé : ni base, ni journal [EF-40, US-21].
 */
export interface SituateRequest {
  region: string;
  taille_menage: number;
  depenses_mensuelles: "moins_50k" | "50k_100k" | "100k_200k" | "200k_350k" | "350k_500k" | "plus_500k";
  niveau_instruction_chef?: ("aucun" | "primaire" | "moyen" | "secondaire" | "superieur") | null;
}
