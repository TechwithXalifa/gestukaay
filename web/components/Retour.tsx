"use client";

import { useState } from "react";
import type { FeedbackRequest } from "@contracts/feedback_request";
import { envoyerRetour } from "@/lib/api";
import { Drapeau, Pouce } from "./icones";

type Motif = NonNullable<FeedbackRequest["motif"]>;
const MOTIFS: [Motif, string][] = [
  ["chiffre_faux", "Le chiffre me semble faux"],
  ["mauvaise_zone", "Ce n'est pas la bonne zone"],
  ["mauvaise_comprehension", "Ma question a été mal comprise"],
  ["autre", "Autre chose"],
];

/** Vote et signalement (EF-49 à EF-51). */
export function Retour({ reponseId }: { reponseId: string }) {
  const [etat, setEtat] = useState<"repos" | "signaler" | "merci" | "erreur">("repos");
  const [motif, setMotif] = useState<Motif>("chiffre_faux");
  const [commentaire, setCommentaire] = useState("");

  async function envoyer(retour: Omit<FeedbackRequest, "reponse_id">) {
    try {
      await envoyerRetour({ reponse_id: reponseId, ...retour });
      setEtat("merci");
    } catch {
      setEtat("erreur");
    }
  }

  if (etat === "merci") return <p className="retour" role="status">Merci, votre retour a été transmis à l'équipe.</p>;

  if (etat === "signaler")
    return (
      <form
        className="signaler"
        onSubmit={(e) => {
          e.preventDefault();
          envoyer({ type: "signalement", motif, commentaire: commentaire.trim() || null });
        }}
      >
        <fieldset>
          <legend>Qu'est-ce qui ne va pas ?</legend>
          {MOTIFS.map(([valeur, libelle]) => (
            <label key={valeur}>
              <input type="radio" name="motif" checked={motif === valeur} onChange={() => setMotif(valeur)} />
              {libelle}
            </label>
          ))}
        </fieldset>
        <label htmlFor="commentaire">Précisez (facultatif)</label>
        <textarea id="commentaire" maxLength={1000} value={commentaire} onChange={(e) => setCommentaire(e.target.value)} />
        <div className="actions">
          <button type="submit" className="primaire">Envoyer le signalement</button>
          <button type="button" className="tertiaire" onClick={() => setEtat("repos")}>Annuler</button>
        </div>
      </form>
    );

  return (
    <div className="retour">
      <span>Cette réponse vous a-t-elle été utile ?</span>
      <button type="button" className="secondaire petit" onClick={() => envoyer({ type: "vote", vote: "utile" })}>
        <Pouce taille={16} />Oui
      </button>
      <button type="button" className="secondaire petit" onClick={() => envoyer({ type: "vote", vote: "pas_utile" })}>
        <Pouce taille={16} bas />Non
      </button>
      <button type="button" className="tertiaire lien-signaler" onClick={() => setEtat("signaler")}>
        <Drapeau taille={16} />Signaler une erreur
      </button>
      {etat === "erreur" && <span role="alert">L'envoi a échoué, réessayez.</span>}
    </div>
  );
}
