import { API_URL } from "./api";

/**
 * Réponse vocale sur le site (décision 0040). L'API donne le chemin de la note (`/v1/answers/{id}/audio.ogg`),
 * calculée à la demande : on la complète avec l'adresse de l'API.
 */
export const adresseAudio = (url: string) => new URL(url, API_URL).toString();

const CLE = "gestukaay.ecouter";

/** La réponse vient d'une question posée à la voix, sur cet appareil : sa note pourra démarrer seule. */
export function aEcouter(audioUrl: string | null | undefined) {
  if (!audioUrl) return;
  try {
    sessionStorage.setItem(CLE, audioUrl);
  } catch {
    // stockage bloqué (navigation privée) : le bouton « Écouter » reste
  }
}

/** Vrai une seule fois, juste après la question vocale : une réponse rouverte par son lien ne parle jamais seule. */
export function ecouterMaintenant(audioUrl: string): boolean {
  try {
    if (sessionStorage.getItem(CLE) !== audioUrl) return false;
    sessionStorage.removeItem(CLE);
    return true;
  } catch {
    return false;
  }
}

/** Téléphone ou tablette (écran tactile, pas de souris) : lecture automatique ; ordinateur : bouton « Écouter ». */
export const ecranTactile = () =>
  typeof window !== "undefined" && window.matchMedia("(hover: none) and (pointer: coarse)").matches;
