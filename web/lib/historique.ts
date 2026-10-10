import type { AskResponse } from "@contracts/ask_response";

/**
 * Dernières réponses consultées, gardées sur l'appareil pour rester lisibles
 * hors ligne (7.3). Rien n'est envoyé au serveur ; un stockage indisponible
 * (navigation privée, données bloquées) ne casse jamais la page.
 */
const CLE = "gestukaay.historique";
const MAX = 20;

export type Consultation = { reponse: AskResponse; consulteeLe: string };

function lire(): Consultation[] {
  try {
    return JSON.parse(localStorage.getItem(CLE) ?? "[]");
  } catch {
    return [];
  }
}

export function memoriser(reponse: AskResponse): void {
  try {
    const autres = lire().filter((c) => c.reponse.reponse.id !== reponse.reponse.id);
    const liste = [{ reponse, consulteeLe: new Date().toISOString() }, ...autres].slice(0, MAX);
    localStorage.setItem(CLE, JSON.stringify(liste));
  } catch {
    /* stockage plein ou bloqué : la page reste utilisable */
  }
}

export const historique = (): Consultation[] => lire();

export const retrouver = (id: string): AskResponse | null =>
  lire().find((c) => c.reponse.reponse.id === id)?.reponse ?? null;

/** « Mes chiffres » : oublier une consultation, ou tout l'historique de l'appareil. */
export function oublier(id: string): void {
  try {
    localStorage.setItem(CLE, JSON.stringify(lire().filter((c) => c.reponse.reponse.id !== id)));
  } catch {
    /* stockage bloqué : rien à oublier */
  }
}

export function effacerHistorique(): void {
  try {
    localStorage.removeItem(CLE);
  } catch {
    /* stockage bloqué : rien à effacer */
  }
}
