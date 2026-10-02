"use client";

import { useState } from "react";
import type { FeedbackRequest } from "@contracts/feedback_request";
import { useLangue } from "@/i18n/langue";
import { envoyerRetour } from "@/lib/api";
import { Drapeau, Pouce } from "./icones";

type Motif = NonNullable<FeedbackRequest["motif"]>;
const MOTIFS: Motif[] = ["chiffre_faux", "mauvaise_zone", "mauvaise_comprehension", "autre"];

/** Vote et signalement (EF-49 à EF-51). */
export function Retour({ reponseId }: { reponseId: string }) {
  const { t } = useLangue();
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

  if (etat === "merci") return <p className="retour" role="status">{t("retour.merci")}</p>;

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
          <legend>{t("retour.quoi")}</legend>
          {MOTIFS.map((valeur) => (
            <label key={valeur}>
              <input type="radio" name="motif" checked={motif === valeur} onChange={() => setMotif(valeur)} />
              {t(`retour.${valeur}`)}
            </label>
          ))}
        </fieldset>
        <label htmlFor="commentaire">{t("retour.preciser")}</label>
        <textarea id="commentaire" maxLength={1000} value={commentaire} onChange={(e) => setCommentaire(e.target.value)} />
        <div className="actions">
          <button type="submit" className="primaire">{t("retour.envoyer")}</button>
          <button type="button" className="tertiaire" onClick={() => setEtat("repos")}>{t("retour.annuler")}</button>
        </div>
      </form>
    );

  return (
    <div className="retour">
      <span>{t("retour.question")}</span>
      <button type="button" className="secondaire petit" onClick={() => envoyer({ type: "vote", vote: "utile" })}>
        <Pouce taille={16} />{t("retour.oui")}
      </button>
      <button type="button" className="secondaire petit" onClick={() => envoyer({ type: "vote", vote: "pas_utile" })}>
        <Pouce taille={16} bas />{t("retour.non")}
      </button>
      <button type="button" className="tertiaire lien-signaler" onClick={() => setEtat("signaler")}>
        <Drapeau taille={16} />{t("retour.signaler")}
      </button>
      {etat === "erreur" && <span role="alert">{t("retour.echec")}</span>}
    </div>
  );
}
