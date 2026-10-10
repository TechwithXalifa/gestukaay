"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useLangue } from "@/i18n/langue";
import { suggerer, type Suggestion } from "@/lib/api";
import { insecables } from "@/lib/typo";
import { Donnees, Fleche, Micro, Question, Tourne } from "./icones";

/** Attente après la dernière frappe avant de demander des suggestions : une requête par pause, pas par lettre. */
const PAUSE_MS = 180;

/**
 * Champ de question (9.7) : 16 px minimum, libellé accessible, micro toujours présent.
 * Autocomplétion (EF-10) : pendant la frappe, des questions qui marchent (questions types vérifiées, indicateurs
 * du catalogue). Motif combobox de l'ARIA : flèches pour choisir, Entrée pour poser, Échap pour fermer. Une
 * suggestion indisponible (API lente, hors ligne) ne gêne jamais la saisie : la liste ne s'affiche pas.
 */
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
  const { t } = useLangue();
  const id = useId();
  const [question, setQuestion] = useState(initiale);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [ouvert, setOuvert] = useState(false);
  const [actif, setActif] = useState(-1);
  // Pas de suggestions pour la question déjà posée (page réponse) tant que l'usager n'a rien tapé
  const tape = useRef(false);
  const valide = question.trim().length >= 3;

  useEffect(() => {
    const q = question.trim();
    if (!tape.current || desactive || q.length < 2) {
      setSuggestions([]);
      return;
    }
    const arret = new AbortController();
    const minuteur = setTimeout(() => {
      suggerer(q, arret.signal)
        .then((r) => {
          if (!tape.current) return; // question envoyée entre-temps : la liste ne revient pas
          // Rien à proposer qui ne soit déjà écrit tel quel
          const utiles = r.suggestions.filter((s) => s.texte.toLowerCase() !== q.toLowerCase());
          setSuggestions(utiles);
          setActif(-1);
          setOuvert(utiles.length > 0);
        })
        .catch(() => setSuggestions([]));
    }, PAUSE_MS);
    return () => {
      clearTimeout(minuteur);
      arret.abort();
    };
  }, [question, desactive]);

  const visible = ouvert && suggestions.length > 0 && !enCours && !desactive;
  const idListe = `${id}-suggestions`;
  const idOption = (i: number) => `${id}-suggestion-${i}`;

  function poser(texte: string) {
    setOuvert(false);
    setSuggestions([]);
    tape.current = false;
    setQuestion(texte);
    onEnvoyer(texte);
  }

  function clavier(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!visible) {
      if (e.key === "ArrowDown" && suggestions.length > 0) setOuvert(true);
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const pas = e.key === "ArrowDown" ? 1 : -1;
      // -1 : retour au texte tapé, comme dans un moteur de recherche
      setActif((a) => ((a + pas + 1 + suggestions.length + 1) % (suggestions.length + 1)) - 1);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOuvert(false);
    } else if (e.key === "Enter" && actif >= 0) {
      e.preventDefault();
      poser(suggestions[actif].texte);
    } else if (e.key === "Tab") {
      setOuvert(false);
    }
  }

  return (
    <div className="champ-zone">
      <form
        className={`champ${grand ? " grand" : ""}${desactive ? " desactive" : ""}`}
        onSubmit={(e) => {
          e.preventDefault();
          if (valide && !enCours && !desactive) poser(question.trim());
        }}
      >
        <label htmlFor="question" className="sr-only">{t("champ.libelle")}</label>
        <input
          id="question"
          value={question}
          onChange={(e) => {
            tape.current = true;
            setQuestion(e.target.value);
          }}
          onKeyDown={clavier}
          onBlur={() => setOuvert(false)}
          onFocus={() => suggestions.length > 0 && setOuvert(true)}
          placeholder={t(desactive ? "champ.horsligne" : "champ.exemple")}
          maxLength={300}
          autoComplete="off"
          disabled={desactive}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={visible}
          aria-controls={idListe}
          aria-activedescendant={visible && actif >= 0 ? idOption(actif) : undefined}
        />
        {onMicro && (
          <button type="button" className="bouton-icone micro" aria-label={t("champ.micro")} onClick={onMicro} disabled={desactive}>
            <Micro />
          </button>
        )}
        {/* Pendant la recherche, le bouton tourne là où l'on vient de cliquer (les étapes peuvent être plus bas) */}
        <button
          type="submit"
          className={enCours ? "bouton-icone occupe" : "bouton-icone"}
          aria-label={t(enCours ? "etat.recherche" : "champ.envoyer")}
          disabled={!valide || enCours || desactive}
        >
          {enCours ? <Tourne /> : <Fleche />}
        </button>
      </form>
      <ul id={idListe} role="listbox" aria-label={t("champ.suggestions")} className="suggestions-champ" hidden={!visible}>
        {visible &&
          suggestions.map((s, i) => (
            <li
              key={s.texte}
              id={idOption(i)}
              role="option"
              aria-selected={i === actif}
              className={i === actif ? "actif" : undefined}
              // mousedown : choisi avant que le champ perde le focus (et ferme la liste)
              onMouseDown={(e) => {
                e.preventDefault();
                poser(s.texte);
              }}
              onMouseEnter={() => setActif(i)}
            >
              {s.indicateur ? <Donnees taille={18} /> : <Question taille={18} />}
              <span>
                {insecables(s.texte)}
                {s.indicateur && <small>{t("champ.suggestionIndicateur")}</small>}
              </span>
            </li>
          ))}
      </ul>
      <p className="sr-only" role="status" aria-live="polite">
        {visible ? t("champ.suggestionsN", { n: String(suggestions.length) }) : ""}
      </p>
    </div>
  );
}
