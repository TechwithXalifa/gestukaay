/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */

/**
 * Réponse de POST /v1/transcrire [EF-11, EF-15, US-09].
 *
 * Corps de la requête : multipart, champ `fichier` (WebM/OGG Opus, 60 s
 * max) et champ facultatif `langue` (fr | wo | auto). L'audio n'est pas
 * conservé (10.7). Le web affiche `transcription`, l'utilisateur la corrige,
 * puis envoie POST /v1/ask avec source="voix".
 */
export interface TranscriptionResponse {
  version_contrat: string;
  transcription: string;
  langue: "fr" | "wo";
  duree_s: number;
  confiance: number | null;
}
