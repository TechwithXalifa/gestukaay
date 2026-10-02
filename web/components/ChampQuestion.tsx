"use client";

import { useState } from "react";
import { Fleche, Micro } from "./icones";

/** Champ de question (9.7) : 16 px minimum, libellé accessible, micro toujours présent. */
export function ChampQuestion({
  initiale = "",
  enCours = false,
  desactive = false,
  onEnvoyer,
  onMicro,
  grand = false,
}: {
  initiale?: string;
  enCours?: boolean;
  desactive?: boolean;
  onEnvoyer: (question: string) => void;
  onMicro?: () => void;
  grand?: boolean;
}) {
  const [question, setQuestion] = useState(initiale);
  const valide = question.trim().length >= 3;
  return (
    <form
      className={`champ${grand ? " grand" : ""}${desactive ? " desactive" : ""}`}
      onSubmit={(e) => {
        e.preventDefault();
        if (valide && !enCours && !desactive) onEnvoyer(question.trim());
      }}
    >
      <label htmlFor="question" className="sr-only">Votre question</label>
      <input
        id="question"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder={desactive ? "Question indisponible hors ligne" : "Combien d'habitants à Thiès ?"}
        maxLength={300}
        autoComplete="off"
        disabled={desactive}
      />
      {onMicro && (
        <button type="button" className="bouton-icone micro" aria-label="Poser la question à voix haute" onClick={onMicro} disabled={desactive}>
          <Micro />
        </button>
      )}
      <button type="submit" className="bouton-icone" aria-label="Envoyer la question" disabled={!valide || enCours || desactive}>
        <Fleche />
      </button>
    </form>
  );
}
