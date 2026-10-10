import type { ValeurCle } from "./api";
import { REGIONS } from "./regions";

/** Les zones qui ont une fiche « Ma région en chiffres » : le Sénégal et les 14 régions (profil_zone.py). */
export const ZONES_FICHE = [{ code: "SN", libelle: "Sénégal" }, ...REGIONS];

export const libelleZone = (code: string) => ZONES_FICHE.find((z) => z.code === code)?.libelle ?? code;

/** Les chiffres clés rangés par thème, dans l'ordre où l'API les donne. */
export function parTheme(chiffres: ValeurCle[]): [string, ValeurCle[]][] {
  const themes = new Map<string, ValeurCle[]>();
  for (const c of chiffres) themes.set(c.theme, [...(themes.get(c.theme) ?? []), c]);
  return [...themes.entries()];
}

/** Rang écrit en toutes lettres : « 1re », « 2e »… (typographie française). */
export const ordinal = (n: number) => (n === 1 ? "1re" : `${n}e`);
