/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */

/**
 * Corps de POST /v1/ask [EF-01].
 */
export interface AskRequest {
  question: string;
  langue?: ("fr" | "wo") | "auto";
  canal?: "web" | "whatsapp" | "telegram" | "api";
  conversation_id?: string | null;
  audio_retour?: boolean;
  source?: "texte" | "voix";
  transcription_brute?: string | null;
}
