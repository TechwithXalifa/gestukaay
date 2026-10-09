"use client";

import { useState } from "react";
import type { AskResponse, ReponseExacte } from "@contracts/ask_response";
import { useLangue } from "@/i18n/langue";
import { envoyerRetour } from "@/lib/api";
import { uniteAmbigue } from "@/lib/unites";
import { Actions } from "./Actions";
import { Graphique } from "./Graphique";
import { LecteurAudio } from "./LecteurAudio";
import { Retour } from "./Retour";
import { chiffres, insecables } from "@/lib/typo";
import { Base, Certifie, Externe, Fleche, Info, Livre, Micro, Tendance } from "./icones";

type R = AskResponse["reponse"];

/** Carte réponse : trois issues, et seulement trois (contrat §3). */
export function Reponse({
  r,
  onChoix,
  onQuestion,
  onMicro,
}: {
  r: R;
  onChoix: (id: string) => void;
  onQuestion: (question: string) => void;
  onMicro?: () => void;
}) {
  const { t } = useLangue();
  switch (r.issue) {
    case "exacte":
      return <Exacte r={r} />;
    case "approchee":
      return (
        <article className="carte" aria-labelledby="titre-reponse">
          <span className="badge approchee"><Info taille={16} />{t("reponse.approchee")}</span>
          <p id="titre-reponse" className="explication">{insecables(r.reformulation)}</p>
          <div className="choix">
            {r.choix.map((c) => (
              <button key={c.id} type="button" className="secondaire" onClick={() => onChoix(c.id)}>
                {insecables(c.libelle)}
              </button>
            ))}
          </div>
        </article>
      );
    case "aucune":
      // Conversation (0033) : une bulle, pas un refus. Incompréhension (7.3) : exemples et micro.
      if (r.motif === "conversation")
        return (
          <article className="carte bulle-conversation" aria-labelledby="titre-reponse">
            <h1 id="titre-reponse" className="texte-conversation">{insecables(r.message)}</h1>
            <Suggestions r={r} onQuestion={onQuestion} />
          </article>
        );
      if (r.motif === "incomprehension")
        return (
          <article className="carte" aria-labelledby="titre-reponse">
            <span className="pastille-icone"><Info taille={24} /></span>
            {/* En wolof, le message du moteur seul : pas de titre français au-dessus (revue de KBD) */}
            {r.langue === "wo" ? (
              <h1 id="titre-reponse" className="titre-etat" lang="wo">{insecables(r.message)}</h1>
            ) : (
              <h1 id="titre-reponse" className="titre-etat">{t("reponse.incompris")}</h1>
            )}
            <p className="explication">{t("reponse.incomprisAide")}</p>
            <div className="exemples gauche">
              {EXEMPLES_INCOMPRIS.map((e) => (
                <button key={e.texte} type="button" className="puce" onClick={() => onQuestion(e.texte)}>
                  {e.wo && <span className="marqueur-wo">WO</span>}
                  <span lang={e.wo ? "wo" : undefined}>{insecables(e.texte)}</span>
                </button>
              ))}
            </div>
            {onMicro && (
              <button type="button" className="secondaire bouton-micro-reessayer" onClick={onMicro}>
                <Micro taille={18} />{t("reponse.micro")}
              </button>
            )}
          </article>
        );
      return (
        <article className="carte" aria-labelledby="titre-reponse">
          <span className="pastille-icone"><Base taille={24} /></span>
          <h1 id="titre-reponse" className="titre-etat">{insecables(r.message)}</h1>
          <Suggestions r={r} onQuestion={onQuestion} />
          {/* EF-51 : suggérer un indicateur n'a de sens que s'il manque au socle */}
          {r.motif === "hors_socle" && <SuggererIndicateur reponseId={r.id} question={r.question} />}
        </article>
      );
  }
}

const EXEMPLES_INCOMPRIS = [
  { texte: "Combien d'habitants à Thiès ?" },
  { texte: "Quel est le taux de pauvreté à Kolda ?" },
  { texte: "Ñaata nit ñoo dëkk Tiés ?", wo: true },
];

function Suggestions({ r, onQuestion }: { r: Extract<R, { issue: "aucune" }>; onQuestion: (q: string) => void }) {
  if (r.suggestions.length === 0) return null;
  return (
    <ul className="suggestions">
      {r.suggestions.map((s) => (
        <li key={s.indicateur.code}>
          <button type="button" onClick={() => onQuestion(s.question_suggeree)}>
            <span>
              <strong>{insecables(s.question_suggeree)}</strong>
              <small>{s.indicateur.libelle}</small>
            </span>
            <Fleche />
          </button>
        </li>
      ))}
    </ul>
  );
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
  // Classement (5.4) : la zone demandée en grand, les autres dans les barres triées. Quatorze
  // chiffres géants les uns sous les autres repoussaient le graphique trois écrans plus bas.
  const classement = r.intention === "classement" && !!r.graphique && r.resultats.length > 1;
  // Le moteur trie par valeur : la zone demandée est celle mise en évidence, pas forcément la première.
  const affiches = classement ? [r.resultats.find((v) => v.mise_en_evidence) ?? r.resultats[0]] : r.resultats;
  return (
    <article className="carte reponse" aria-labelledby="titre-reponse">
      <div className="ligne-badges">
        <span className="badge exacte"><Certifie taille={16} />{t("reponse.exacte")}</span>
        {nonObservee?.nature && (
          <span className="badge projection"><Tendance taille={16} />{t(nonObservee.nature === "projection" ? "reponse.projection" : "reponse.estimation")}</span>
        )}
      </div>
      {nonObservee?.base_projection && (
        <p className="note">{t("reponse.base", { base: nonObservee.base_projection })}</p>
      )}

      {affiches.map((v, i) => {
        // Un seul titre de niveau 1 par page : les résultats suivants (comparaison, taux compagnon
        // d'un nombre, décision 0024) sont des titres de niveau 2, même apparence.
        const Titre = i === 0 ? "h1" : "h2";
        return (
        <div key={v.observation_id} className="resultat">
          <Titre id={i === 0 ? "titre-reponse" : undefined} className="libelle">
            {v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}
            {r.periode_par_defaut && ` · ${t("reponse.derniere")}`}
          </Titre>
          {/* Le chiffre officiel s'affiche d'emblée, jamais une valeur intermédiaire (revue UI du 08/10 :
              un compteur montrait « 197 156 habitants » au lieu de 2 463 677). Au-delà de 11 caractères
              (montants en millions de FCFA), il passe à la taille « longue » pour tenir sur un téléphone. */}
          <p className={v.valeur_affichee.length > 11 ? "valeur longue" : "valeur"}>
            <span>{chiffres(v.valeur_affichee)}</span>{" "}
            {v.unite ? <span className="unite">{v.unite}</span>
              : uniteAmbigue(v) && <span className="unite sans-unite">{t("reponse.sansUnite")}</span>}
          </p>
          <p className="source-ligne">
            <Livre taille={16} />
            <span>{v.source.libelle}</span>
          </p>
        </div>
        );
      })}
      {classement && <p className="note">{t("reponse.classement", { n: String(r.resultats.length) })}</p>}
      <p className="explication">{insecables(r.explication)}</p>
      {r.audio_url && <LecteurAudio url={r.audio_url} langue={r.langue} />}

      {/* Partager vient juste sous le chiffre : sur mobile, la barre était 1,4 écran plus bas (revue UI) */}
      <Actions id={r.id} citation={r.citation} url={r.url} />

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

      <Retour reponseId={r.id} />
    </article>
  );
}
