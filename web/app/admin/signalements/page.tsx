"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { appelAdmin, Cadre, Choix, Connexion, useAdmin } from "@/components/Admin";

/**
 * Relecture des signalements (back-office, route /admin/signalements) : « chiffre faux », « mauvaise zone »… et
 * suggestions d'indicateur, avec leur question. Chacun passe de « À traiter » à « En cours », « Corrigé » ou
 * « Rejeté », avec une note (le numéro de la PR qui corrige, la raison du rejet) ; le back-office garde qui l'a
 * fait et quand. Les arrivées par semaine montrent la tendance.
 */
type Statut = "a_traiter" | "en_cours" | "corrige" | "rejete";
type Retour = {
  reponse_id: string;
  recu_le: string;
  type: "signalement" | "suggestion_indicateur";
  motif: string | null;
  commentaire: string | null;
  question: string | null;
  issue: string | null;
  indicateur: string | null;
  langue: string | null;
  canal: string | null;
  statut: Statut;
  note: string | null;
  par: string | null;
  le: string | null;
};
type Donnees = { comptes: Record<Statut, number>; par_semaine: { il_y_a: number; recus: number }[]; lignes: Retour[] };

const STATUTS: Record<Statut, string> = { a_traiter: "À traiter", en_cours: "En cours", corrige: "Corrigé", rejete: "Rejeté" };
const TYPES = { signalement: "Signalements", suggestion_indicateur: "Suggestions d'indicateur" };
const MOTIFS: Record<string, string> = {
  chiffre_faux: "Chiffre faux",
  mauvaise_zone: "Mauvaise zone",
  mauvaise_comprehension: "Question mal comprise",
  autre: "Autre",
};
const PERIODES = [30, 90, 365] as const;
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" });

export default function Signalements() {
  const { identifiant, role, avis, connecter, fermer, appeler } = useAdmin();
  const [statut, setStatut] = useState<Statut>("a_traiter");
  const [type, setType] = useState("");
  const [jours, setJours] = useState<(typeof PERIODES)[number]>(90);
  const [donnees, setDonnees] = useState<Donnees | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    const p = new URLSearchParams({ statut, jours: String(jours) });
    if (type) p.set("type", type);
    appeler(`/admin/signalements?${p}`)
      .then((r) => r.json())
      .then((d: Donnees) => {
        setDonnees(d);
        setErreur(null);
      })
      .catch((e: Error) => setErreur(e.message));
  }, [appeler, statut, type, jours]);

  useEffect(() => {
    if (identifiant) charger();
  }, [identifiant, charger]);

  const cle = (r: Retour) => `${r.reponse_id}|${r.recu_le}|${r.type}`;

  async function suivre(r: Retour, nouveau: Statut) {
    const reponse = await appelAdmin("/admin/signalements/suivi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reponse_id: r.reponse_id, recu_le: r.recu_le, type: r.type, statut: nouveau, note: notes[cle(r)] ?? r.note ?? "" }),
    }).catch(() => null);
    if (!reponse?.ok) setErreur("Le suivi n'a pas pu être enregistré.");
    charger();
  }

  if (!identifiant) {
    return (
      <Cadre actif="signalements">
        <Connexion erreur={avis ?? erreur} verification={identifiant === undefined} onConnecter={connecter} />
      </Cadre>
    );
  }

  const max = donnees ? Math.max(1, ...donnees.par_semaine.map((s) => s.recus)) : 1;

  return (
    <Cadre actif="signalements" identifiant={identifiant} role={role} onFermer={() => { fermer(); setDonnees(null); }}>
      <div className="admin-titre">
        <h1 className="titre-etat">Relecture des signalements</h1>
        <div role="group" aria-label="Période" className="bascule admin-periode">
          {PERIODES.map((j) => (
            <button key={j} type="button" aria-pressed={jours === j} onClick={() => setJours(j)}>{j === 365 ? "1 an" : `${j} j`}</button>
          ))}
        </div>
      </div>

      <div className="admin-filtres">
        <div role="group" aria-label="Statut" className="bascule admin-periode admin-statuts">
          {(Object.keys(STATUTS) as Statut[]).map((s) => (
            <button key={s} type="button" aria-pressed={statut === s} onClick={() => setStatut(s)}>
              {STATUTS[s]} ({donnees?.comptes[s] ?? 0})
            </button>
          ))}
        </div>
        <Choix libelle="Type" valeur={type} onChange={setType} options={TYPES} tous="Tous" />
      </div>

      {donnees && (
        <section className="admin-panneau" aria-labelledby="titre-tendance">
          <h2 id="titre-tendance" className="sous-titre">Arrivées par semaine (8 dernières)</h2>
          <div className="admin-histo" aria-hidden="true">
            {donnees.par_semaine.map((s) => <span key={s.il_y_a} style={{ height: `${(s.recus / max) * 100}%` }} title={`${s.recus}`} />)}
          </div>
          <p className="note">
            {donnees.par_semaine.map((s) => s.recus).join(" · ")} (de la plus ancienne à la semaine en cours)
          </p>
        </section>
      )}

      {erreur && <p className="erreur-admin" role="alert">{erreur}</p>}
      {donnees?.lignes.length === 0 && <p className="note">Rien dans « {STATUTS[statut]} » sur la période.</p>}
      <ul className="admin-groupes">
        {donnees?.lignes.map((r) => (
          <li key={cle(r)} className="admin-panneau admin-signalement">
            <p className="note">
              <span className="badge">{r.type === "signalement" ? MOTIFS[r.motif ?? ""] ?? "Signalement" : "Suggestion d'indicateur"}</span>
              {" "}{date.format(new Date(r.recu_le))}{r.canal ? ` · ${r.canal}` : ""}{r.langue ? ` · ${r.langue.toUpperCase()}` : ""}
            </p>
            <h2 className="admin-signalement-question">{r.question ?? "Question introuvable"}</h2>
            {r.commentaire && <p className="admin-commentaire">{r.commentaire}</p>}
            <p className="note">
              {r.issue ? `Issue : ${r.issue}` : ""}{r.indicateur ? ` · ${r.indicateur}` : ""}
              {" · "}<Link href={`/r/${r.reponse_id}`} target="_blank" className="lien">Voir la réponse</Link>
            </p>
            {r.par && (
              <p className="note">{STATUTS[r.statut]} par {r.par}{r.le ? ` le ${date.format(new Date(r.le))}` : ""}{r.note ? ` : ${r.note}` : ""}</p>
            )}
            <label className="admin-champ">
              <span>Note (facultative)</span>
              <input
                value={notes[cle(r)] ?? r.note ?? ""}
                onChange={(e) => setNotes({ ...notes, [cle(r)]: e.target.value })}
                maxLength={1000}
                placeholder="Corrigé par la PR #…, ou raison du rejet"
              />
            </label>
            <div className="admin-signalement-actions">
              {(Object.keys(STATUTS) as Statut[]).filter((s) => s !== r.statut).map((s) => (
                <button key={s} type="button" className="secondaire petit" onClick={() => suivre(r, s)}>{STATUTS[s]}</button>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </Cadre>
  );
}
