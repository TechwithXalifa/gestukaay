import type { AskResponse } from "@contracts/ask_response";

type R = AskResponse["reponse"];

export function Reponse({
  r,
  onChoix,
  onSuggestion,
}: {
  r: R;
  onChoix: (id: string) => void;
  onSuggestion: (question: string) => void;
}) {
  switch (r.issue) {
    case "exacte":
      return (
        <article className="carte">
          <span className="badge exacte">✓ Correspondance exacte</span>
          {r.resultats.map((v) => (
            <div key={v.observation_id}>
              <p className="libelle">
                {v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}
                {r.periode_par_defaut && " (dernière donnée publiée)"}
              </p>
              <p className="valeur">
                {v.valeur_affichee} <span>{v.unite}</span>
              </p>
              <p className="source">{v.source.libelle}</p>
            </div>
          ))}
          <p className="explication">{r.explication}</p>
          {r.note_perimetre && <p className="source">Périmètre : {r.note_perimetre}</p>}
          <p className="source">{r.citation}</p>
        </article>
      );
    case "approchee":
      return (
        <article className="carte">
          <span className="badge approchee">ⓘ Correspondance approchée</span>
          <p className="explication">{r.reformulation}</p>
          <div className="choix">
            {r.choix.map((c) => (
              <button key={c.id} className="secondaire" onClick={() => onChoix(c.id)}>
                {c.libelle}
              </button>
            ))}
          </div>
        </article>
      );
    case "aucune":
      return (
        <article className="carte">
          <p className="explication">{r.message}</p>
          <div className="choix">
            {r.suggestions.map((s) => (
              <button
                key={s.indicateur.code}
                className="secondaire"
                onClick={() => onSuggestion(s.question_suggeree)}
              >
                {s.question_suggeree}
              </button>
            ))}
          </div>
        </article>
      );
  }
}
