import type { SituateResponse } from "@contracts/situate_response";

type Resultat = SituateResponse["moyenne_region"];

/**
 * Schéma des 14 régions en tuiles (décision 0039) : positions approximatives, nord en haut, la Gambie
 * entre les rangées 3 et 4. Ce n'est pas une carte : le dépôt n'a pas de fond géographique, et une
 * tuile par région se lit et se touche mieux sur un téléphone.
 */
export const TUILES: Record<string, { ligne: number; colonne: number }> = {
  "SN-SL": { ligne: 1, colonne: 3 },
  "SN-LG": { ligne: 2, colonne: 3 }, "SN-MT": { ligne: 2, colonne: 4 },
  "SN-DK": { ligne: 3, colonne: 1 }, "SN-TH": { ligne: 3, colonne: 2 }, "SN-DB": { ligne: 3, colonne: 3 },
  "SN-FK": { ligne: 4, colonne: 2 }, "SN-KL": { ligne: 4, colonne: 3 }, "SN-KA": { ligne: 4, colonne: 4 },
  "SN-TC": { ligne: 4, colonne: 5 },
  "SN-ZG": { ligne: 5, colonne: 2 }, "SN-SE": { ligne: 5, colonne: 3 }, "SN-KD": { ligne: 5, colonne: 4 },
  "SN-KE": { ligne: 5, colonne: 5 },
};

/**
 * Classe de couleur (1 à 5) d'une valeur, par intervalles égaux entre la plus petite et la plus grande
 * moyenne publiée. Sert seulement à colorer : aucune borne de classe n'est affichée (zéro chiffre fabriqué),
 * chaque tuile porte sa valeur publiée.
 */
export function classe(valeur: number, valeurs: number[]): number {
  const min = Math.min(...valeurs);
  const max = Math.max(...valeurs);
  if (max === min) return 3;
  return Math.min(5, 1 + Math.floor(((valeur - min) / (max - min)) * 5));
}

/** Position en % d'une valeur sur l'axe du graphique (0 à `max`). */
export const pourcent = (v: number, max: number) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`;

/** Le haut de l'axe : la plus grande valeur affichée, arrondie au palier supérieur (axe seulement). */
export function hautDeLAxe(valeurs: number[]): number {
  const max = Math.max(...valeurs, 1);
  const pas = max > 500_000 ? 250_000 : max > 100_000 ? 100_000 : 10_000;
  return Math.ceil((max * 1.05) / pas) * pas;
}

export type { Resultat };
