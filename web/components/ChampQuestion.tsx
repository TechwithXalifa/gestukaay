"use client";

import { useState } from "react";
import { Fleche } from "./icones";

/** Champ de question (9.7) : 16 px minimum, libellé accessible, ombre de marque. */
export function ChampQuestion({
  initiale = "",
  enCours = false,
  onEnvoyer,
  grand = false,
}: {
  initiale?: string;
  enCours?: boolean;
  onEnvoyer: (question: string) => void;
  grand?: boolean;
}) {
  const [question, setQuestion] = useState(initiale);
  const valide = question.trim().length >= 3;
  return (
    <form
      className={grand ? "champ grand" : "champ"}
      onSubmit={(e) => {
        e.preventDefault();
        if (valide && !enCours) onEnvoyer(question.trim());
      }}
    >
      <label htmlFor="question" className="sr-only">Votre question</label>
      <input
        id="question"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Combien d'habitants à Thiès ?"
        maxLength={300}
        autoComplete="off"
      />
      <button type="submit" className="bouton-icone" aria-label="Envoyer la question" disabled={!valide || enCours}>
        <Fleche />
      </button>
    </form>
  );
}
