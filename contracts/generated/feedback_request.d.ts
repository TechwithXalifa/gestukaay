/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */

export interface FeedbackRequest {
  reponse_id: string;
  type: "vote" | "signalement" | "suggestion_indicateur";
  vote?: ("utile" | "pas_utile") | null;
  motif?: ("chiffre_faux" | "mauvaise_zone" | "mauvaise_comprehension" | "autre") | null;
  commentaire?: string | null;
}
