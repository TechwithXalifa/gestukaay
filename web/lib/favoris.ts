import type { ReponseExacte } from "@contracts/ask_response";

/**
 * « Mes chiffres » : les réponses épinglées, gardées sur l'appareil seulement (comme l'historique, 7.3).
 * Rien n'est envoyé au serveur ; un stockage indisponible (navigation privée, données bloquées) ne casse jamais
 * la page. Un événement prévient les autres composants de la page (bouton Épingler, liste).
 */
const CLE = "gestukaay.favoris";
const MAX = 50;
export const EVENEMENT = "gestukaay:favoris";

export type Favori = { r: ReponseExacte; epingleLe: string };

function lire(): Favori[] {
  try {
    const liste = JSON.parse(localStorage.getItem(CLE) ?? "[]");
    return Array.isArray(liste) ? liste : [];
  } catch {
    return [];
  }
}

function ecrire(liste: Favori[]): boolean {
  try {
    localStorage.setItem(CLE, JSON.stringify(liste));
    window.dispatchEvent(new Event(EVENEMENT));
    return true;
  } catch {
    return false; // stockage plein ou bloqué
  }
}

export const favoris = (): Favori[] => lire();

export const estEpingle = (id: string): boolean => lire().some((f) => f.r.id === id);

/** Épingle la réponse (en tête de liste) ; false si l'appareil refuse de la garder. */
export function epingler(r: ReponseExacte): boolean {
  const autres = lire().filter((f) => f.r.id !== r.id);
  return ecrire([{ r, epingleLe: new Date().toISOString() }, ...autres].slice(0, MAX));
}

export function retirer(id: string): void {
  ecrire(lire().filter((f) => f.r.id !== id));
}

/** Tableur des chiffres épinglés : UTF-8 avec BOM et point-virgule, lisible par Excel en français. */
export function versCsv(liste: Favori[]): string {
  const cellule = (v: string) => {
    // Jamais une formule (injection CSV) ; un nombre négatif reste un nombre
    const s = /^[=+\-@\t\r]/.test(v) && !/^-?\d+(,\d+)?$/.test(v) ? `'${v}` : v;
    return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lignes = [["Question", "Indicateur", "Zone", "Période", "Valeur", "Valeur (nombre)", "Unité", "Source", "Adresse"]];
  for (const { r } of liste)
    for (const v of r.resultats)
      lignes.push([r.question, v.indicateur.libelle, v.zone.libelle, v.periode.libelle, v.valeur_affichee,
        String(v.valeur).replace(".", ","), v.unite, v.source.libelle, r.url]);
  return `\ufeff${lignes.map((l) => l.map(cellule).join(";")).join("\r\n")}\r\n`;
}
