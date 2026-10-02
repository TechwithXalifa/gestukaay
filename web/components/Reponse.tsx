import type { AskResponse, ReponseExacte } from "@contracts/ask_response";
import { Actions } from "./Actions";
import { Retour } from "./Retour";
import { Base, Coche, Externe, Fleche, Info, Livre } from "./icones";

type R = AskResponse["reponse"];

/** Carte réponse : trois issues, et seulement trois (contrat §3). */
export function Reponse({
  r,
  onChoix,
  onQuestion,
}: {
  r: R;
  onChoix: (id: string) => void;
  onQuestion: (question: string) => void;
}) {
  switch (r.issue) {
    case "exacte":
      return <Exacte r={r} />;
    case "approchee":
      return (
        <article className="carte" aria-labelledby="titre-reponse">
          <span className="badge approchee"><Info taille={16} />Correspondance approchée</span>
          <p id="titre-reponse" className="explication">{r.reformulation}</p>
          <div className="choix">
            {r.choix.map((c) => (
              <button key={c.id} type="button" className="secondaire" onClick={() => onChoix(c.id)}>
                {c.libelle}
              </button>
            ))}
          </div>
          <p className="note">Gëstukaay ne remplace jamais un chiffre manquant par une estimation. Aucune valeur n'est affichée avant votre choix.</p>
        </article>
      );
    case "aucune":
      return (
        <article className="carte" aria-labelledby="titre-reponse">
          <span className="pastille-icone"><Base taille={24} /></span>
          <h1 id="titre-reponse" className="titre-etat">{r.message}</h1>
          {r.suggestions.length > 0 && (
            <ul className="suggestions">
              {r.suggestions.map((s) => (
                <li key={s.indicateur.code}>
                  <button type="button" onClick={() => onQuestion(s.question_suggeree)}>
                    <span>
                      <strong>{s.question_suggeree}</strong>
                      <small>{s.indicateur.libelle}</small>
                    </span>
                    <Fleche />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>
      );
  }
}

function Exacte({ r }: { r: ReponseExacte }) {
  const sources = [...new Map(r.resultats.map((v) => [v.source.url, v.source])).values()];
  return (
    <article className="carte" aria-labelledby="titre-reponse">
      <div className="ligne-badges">
        <span className="badge exacte"><Coche taille={16} />Correspondance exacte</span>
      </div>

      {r.resultats.map((v, i) => (
        <div key={v.observation_id} className="resultat">
          <h1 id={i === 0 ? "titre-reponse" : undefined} className="libelle">
            {v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}
            {r.periode_par_defaut && " · dernière donnée publiée"}
          </h1>
          <p className="valeur">
            <span>{v.valeur_affichee}</span> <span className="unite">{v.unite}</span>
          </p>
          <p className="source-ligne">
            <Livre taille={16} />
            <span>{v.source.libelle}</span>
          </p>
        </div>
      ))}
      <p className="explication">{r.explication}</p>

      <div className="corps">
        {r.graphique && <p className="note">Graphique : {r.graphique.titre}</p>}
        <aside aria-label="Source officielle" className="bloc-source">
          <p className="bloc-source-titre"><Livre />Source officielle</p>
          {sources.map((s) => (
            <div key={s.url}>
              <p>{s.titre}</p>
              <p className="discret">{s.libelle}</p>
            </div>
          ))}
          {r.note_perimetre && <p className="discret">Périmètre : {r.note_perimetre}</p>}
          <a href={sources[0].url} target="_blank" rel="noreferrer" className="lien">
            Voir la publication <Externe taille={16} />
          </a>
        </aside>
      </div>

      <Actions id={r.id} citation={r.citation} url={r.url} />
      <Retour reponseId={r.id} />
    </article>
  );
}
