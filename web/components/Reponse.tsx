"use client";

import { useState } from "react";
import type { AskResponse, ReponseExacte } from "@contracts/ask_response";
import { useLangue } from "@/i18n/langue";
import { envoyerRetour } from "@/lib/api";
import { Actions } from "./Actions";
import { Graphique } from "./Graphique";
import { LecteurAudio } from "./LecteurAudio";
import { Retour } from "./Retour";
import { Base, Coche, Externe, Fleche, Info, Livre, Tendance } from "./icones";

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
  const { t } = useLangue();
  switch (r.issue) {
    case "exacte":
      return <Exacte r={r} />;
    case "approchee":
      return (
        <article className="carte" aria-labelledby="titre-reponse">
          <span className="badge approchee"><Info taille={16} />{t("reponse.approchee")}</span>
          <p id="titre-reponse" className="explication">{r.reformulation}</p>
          <div className="choix">
            {r.choix.map((c) => (
              <button key={c.id} type="button" className="secondaire" onClick={() => onChoix(c.id)}>
                {c.libelle}
              </button>
            ))}
          </div>
          <p className="note">{t("reponse.sansEstimation")}</p>
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
          <SuggererIndicateur reponseId={r.id} question={r.question} />
        </article>
      );
  }
}

/** EF-51 : depuis un refus, suggérer l'indicateur manquant à l'équipe (maquette M-Refus). */
function SuggererIndicateur({ reponseId, question }: { reponseId: string; question: string }) {
  const { t } = useLangue();
  const [etat, setEtat] = useState<"repos" | "merci" | "erreur">("repos");
  if (etat === "merci") return <p className="retour" role="status">{t("refus.merci")}</p>;
  return (
    <>
      <button
        type="button"
        className="lien-bouton lien-suggerer"
        onClick={() =>
          envoyerRetour({ reponse_id: reponseId, type: "suggestion_indicateur", commentaire: question.slice(0, 1000) })
            .then(() => setEtat("merci"))
            .catch(() => setEtat("erreur"))
        }
      >
        {t("refus.suggerer")} <Fleche taille={16} />
      </button>
      {etat === "erreur" && <p className="note" role="alert">{t("retour.echec")}</p>}
    </>
  );
}

function Exacte({ r }: { r: ReponseExacte }) {
  const { t } = useLangue();
  const sources = [...new Map(r.resultats.map((v) => [v.source.url, v.source])).values()];
  // Décision 0002 : une projection ou une estimation officielle est toujours étiquetée.
  const nonObservee = r.resultats.find((v) => v.nature === "projection" || v.nature === "estimation");
  return (
    <article className="carte" aria-labelledby="titre-reponse">
      <div className="ligne-badges">
        <span className="badge exacte"><Coche taille={16} />{t("reponse.exacte")}</span>
        {nonObservee?.nature && (
          <span className="badge projection"><Tendance taille={16} />{t(nonObservee.nature === "projection" ? "reponse.projection" : "reponse.estimation")}</span>
        )}
      </div>
      {nonObservee?.base_projection && (
        <p className="note">{t("reponse.base", { base: nonObservee.base_projection })}</p>
      )}

      {r.resultats.map((v, i) => (
        <div key={v.observation_id} className="resultat">
          <h1 id={i === 0 ? "titre-reponse" : undefined} className="libelle">
            {v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}
            {r.periode_par_defaut && ` · ${t("reponse.derniere")}`}
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
      {r.audio_url && <LecteurAudio url={r.audio_url} langue={r.langue} />}

      <div className="corps">
        {r.graphique && <Graphique g={r.graphique} />}
        <aside aria-label={t("reponse.source")} className="bloc-source">
          <p className="bloc-source-titre"><Livre />{t("reponse.source")}</p>
          {sources.map((s) => (
            <div key={s.url}>
              <p>{s.titre}</p>
              <p className="discret">{s.libelle}</p>
            </div>
          ))}
          {r.note_perimetre && <p className="discret">{t("reponse.perimetre", { note: r.note_perimetre })}</p>}
          <a href={sources[0].url} target="_blank" rel="noreferrer" className="lien">
            {t("reponse.publication")} <Externe taille={16} />
          </a>
        </aside>
      </div>

      <Actions id={r.id} citation={r.citation} url={r.url} />
      <Retour reponseId={r.id} />
    </article>
  );
}
