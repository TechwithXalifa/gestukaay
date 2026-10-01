"use client";

import { useState } from "react";
import type { AskResponse } from "@contracts/ask_response";
import { confirmer, demander } from "@/lib/api";
import { Reponse } from "@/components/Reponse";

export default function Accueil() {
  const [question, setQuestion] = useState("");
  const [reponse, setReponse] = useState<AskResponse | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  async function lancer(appel: () => Promise<AskResponse>) {
    setEnCours(true);
    setErreur(null);
    try {
      setReponse(await appel());
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Le service ne répond pas.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <main className="page">
      <p className="eyebrow">Données officielles</p>
      <h1>Posez votre question, recevez le chiffre officiel.</h1>
      <form
        className="champ"
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim().length >= 3) lancer(() => demander({ question }));
        }}
      >
        <label htmlFor="question" className="sr-only">Votre question</label>
        <input
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Combien d'habitants à Thiès ?"
          maxLength={300}
        />
        <button type="submit" className="primaire" disabled={enCours}>
          {enCours ? "…" : "Envoyer"}
        </button>
      </form>
      {erreur && <p role="alert" className="alerte">{erreur}</p>}
      {reponse && (
        <Reponse
          r={reponse.reponse}
          onChoix={(id) => lancer(() => confirmer(reponse.reponse.id, id))}
          onSuggestion={(q) => {
            setQuestion(q);
            lancer(() => demander({ question: q }));
          }}
        />
      )}
    </main>
  );
}
