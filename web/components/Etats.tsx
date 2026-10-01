import { ErreurApi } from "@/lib/api";
import { Coche, Tourne } from "./icones";

/** Chargement : étapes visibles et squelettes, jamais un spinner seul (7.3). */
export function Chargement({ question }: { question?: string }) {
  return (
    <section className="carte" aria-busy="true" aria-live="polite">
      <ol className="etapes">
        <li className="fait"><Coche />Question reçue{question ? ` : « ${question} »` : ""}</li>
        <li className="encours"><Tourne />Recherche du chiffre officiel…</li>
      </ol>
      <div aria-hidden="true" className="squelettes">
        <div style={{ width: "42%", height: 12 }} />
        <div style={{ width: "66%", height: 44 }} />
        <div style={{ height: 120 }} />
      </div>
    </section>
  );
}

/** Hors ligne et erreur système : message humain, Réessayer, code discret (7.3). */
export function Erreur({ erreur, onReessayer }: { erreur: unknown; onReessayer: () => void }) {
  const e = erreur instanceof ErreurApi ? erreur : null;
  if (e?.statut === 404)
    return (
      <section className="carte">
        <h1 className="titre-etat">Cette réponse n'existe plus.</h1>
        <p className="explication">Posez à nouveau votre question : la réponse sera recalculée sur les données officielles.</p>
      </section>
    );
  return (
    <section className="carte" role="alert">
      <h1 className="titre-etat">{e?.horsLigne ? "Vous êtes hors ligne." : "Le service ne répond pas pour le moment."}</h1>
      <p className="explication">
        {e?.horsLigne ? "Vérifiez votre connexion, puis réessayez." : "Votre question est conservée. Réessayez dans un instant."}
      </p>
      <button type="button" className="primaire" onClick={onReessayer}>Réessayer</button>
      {e?.codeIncident && <p className="note">Code d'incident : <code>{e.codeIncident}</code> · à indiquer si vous nous contactez</p>}
    </section>
  );
}
