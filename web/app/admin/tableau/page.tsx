"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CANAUX, Cadre, Choix, Connexion, useAdmin } from "@/components/Admin";

/**
 * Tableau de bord du back-office (US-28, maquette BO-Tableau, route /admin/tableau).
 * Indicateurs de qualité calculés sur le journal. L'exactitude et les refus pertinents viennent du
 * benchmark (mesure/rapports) : ils ne sont pas recalculés ici.
 */

type Tableau = {
  jours: number;
  questions: number;
  questions_periode_precedente: number;
  issues: { exacte: number; approchee: number; aucune: number };
  latence_mediane_ms: number | null;
  latence_p95_ms: number | null;
  part_wolof: number | null;
  votes: number;
  satisfaction: number | null;
  signalements: number;
  par_jour: { jour: string; questions: number }[];
  non_resolues: { question: string; langue: string; motif: string; occurrences: number }[];
};

const PERIODES = [7, 30, 90] as const;
const ISSUES = { exacte: "Correspondance exacte", approchee: "Correspondance approchée", aucune: "Refus explicite" } as const;
const MOTIFS: Record<string, string> = {
  hors_socle: "Hors socle",
  projection: "Projection",
  incomprehension: "Incompréhension",
  non_disponible: "Pas encore disponible",
};
const CIBLE_LATENCE_MS = 3000; // ENF-01
const CIBLE_WOLOF = 0.3; // objectif 02 du cahier, à 3 mois
const CIBLE_SATISFACTION = 0.8; // objectif 04

const entier = new Intl.NumberFormat("fr-FR");
const pourcent = new Intl.NumberFormat("fr-FR", { style: "percent", maximumFractionDigits: 0 });
const jourCourt = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" });

function secondes(ms: number | null): string {
  if (ms === null) return "–";
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} s`;
}

function variation(t: Tableau): string {
  if (!t.questions_periode_precedente) return "pas de période précédente à comparer";
  const v = (t.questions - t.questions_periode_precedente) / t.questions_periode_precedente;
  return `${v >= 0 ? "+" : "−"}${pourcent.format(Math.abs(v))} par rapport aux ${t.jours} jours précédents`;
}

export default function TableauDeBord() {
  const { jeton, ouvrir, fermer, appeler } = useAdmin();
  const [jours, setJours] = useState<(typeof PERIODES)[number]>(30);
  const [filtres, setFiltres] = useState({ canal: "", langue: "" });
  const [t, setT] = useState<Tableau | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (!jeton) return;
    let annule = false;
    const p = new URLSearchParams({ jours: String(jours) });
    for (const [k, v] of Object.entries(filtres)) if (v) p.set(k, v);
    appeler(`/admin/tableau?${p}`)
      .then((r) => r.json())
      .then((d) => {
        if (!annule) {
          setT(d);
          setErreur(null);
        }
      })
      .catch((e: Error) => !annule && setErreur(e.message));
    return () => {
      annule = true;
    };
  }, [jeton, jours, filtres, appeler]);

  if (!jeton) {
    return (
      <Cadre actif="tableau">
        <Connexion titre="Tableau de bord" bouton="Ouvrir le tableau de bord" erreur={erreur} onOuvrir={ouvrir} />
      </Cadre>
    );
  }

  const max = t ? Math.max(1, ...t.par_jour.map((j) => j.questions)) : 1;
  const totalIssues = t ? t.issues.exacte + t.issues.approchee + t.issues.aucune : 0;

  return (
    <Cadre actif="tableau" onFermer={() => { fermer(); setT(null); }}>
      <div className="admin-titre">
        <div>
          <h1 className="titre-etat">Tableau de bord</h1>
          <p className="note">{jours} derniers jours · {filtres.canal ? CANAUX[filtres.canal] : "toutes surfaces"}</p>
        </div>
        <div className="admin-filtres">
          <Choix libelle="Canal" valeur={filtres.canal} onChange={(v) => setFiltres((f) => ({ ...f, canal: v }))} options={CANAUX} tous="tous" />
          <Choix libelle="Langue" valeur={filtres.langue} onChange={(v) => setFiltres((f) => ({ ...f, langue: v }))} options={{ fr: "FR", wo: "WO" }} tous="toutes" />
          <div role="group" aria-label="Période" className="bascule admin-periode">
            {PERIODES.map((p) => (
              <button key={p} type="button" aria-pressed={jours === p} onClick={() => setJours(p)}>{p} j</button>
            ))}
          </div>
        </div>
      </div>

      {erreur && <p className="erreur-admin" role="alert">{erreur}</p>}
      {!t && !erreur && <p className="note">Chargement…</p>}

      {t && (
        <>
          <ul className="admin-tuiles">
            <li>
              <span className="admin-tuile-titre">Questions traitées</span>
              <strong>{entier.format(t.questions)}</strong>
              <span className="note">{variation(t)}</span>
            </li>
            <li>
              <span className="admin-tuile-titre">Latence médiane</span>
              <strong className={t.latence_mediane_ms !== null && t.latence_mediane_ms > CIBLE_LATENCE_MS ? "hors-cible" : undefined}>
                {secondes(t.latence_mediane_ms)}
              </strong>
              <span className="note">p95 : {secondes(t.latence_p95_ms)} · cible médiane &lt; 3 s</span>
            </li>
            <li>
              <span className="admin-tuile-titre">Part du wolof</span>
              <strong>{t.part_wolof === null ? "–" : pourcent.format(t.part_wolof)}</strong>
              <span className="note">cible ≥ {pourcent.format(CIBLE_WOLOF)} à 3 mois</span>
            </li>
            <li>
              <span className="admin-tuile-titre">Satisfaction</span>
              <strong className={t.satisfaction !== null && t.satisfaction < CIBLE_SATISFACTION ? "hors-cible" : undefined}>
                {t.satisfaction === null ? "–" : pourcent.format(t.satisfaction)}
              </strong>
              <span className="note">{entier.format(t.votes)} votes · {entier.format(t.signalements)} signalements · cible ≥ 80 %</span>
            </li>
            <li>
              <span className="admin-tuile-titre">Exactitude et refus pertinents</span>
              <strong className="admin-tuile-texte">Mesurés par le benchmark</strong>
              <span className="note">jeu de test de 103 questions · mesure/rapports</span>
            </li>
          </ul>

          <div className="admin-panneaux">
            <section className="admin-panneau" aria-labelledby="titre-par-jour">
              <h2 id="titre-par-jour" className="sous-titre">Questions par jour</h2>
              <div className="admin-histo" aria-hidden="true">
                {t.par_jour.map((j) => (
                  <span key={j.jour} title={`${jourCourt.format(new Date(j.jour))} : ${j.questions}`}
                        style={{ height: `${Math.max((j.questions / max) * 100, j.questions ? 4 : 1)}%` }} />
                ))}
              </div>
              <p className="note admin-histo-axe">
                <span>{jourCourt.format(new Date(t.par_jour[0].jour))}</span>
                <span>{jourCourt.format(new Date(t.par_jour[t.par_jour.length - 1].jour))}</span>
              </p>
              <details>
                <summary>Voir les valeurs par jour</summary>
                <div className="tableau-defile" role="region" aria-label="Questions par jour" tabIndex={0}>
                  <table className="tableau">
                    <thead><tr><th scope="col">Jour</th><th scope="col" className="nombre">Questions</th></tr></thead>
                    <tbody>
                      {t.par_jour.map((j) => (
                        <tr key={j.jour}><th scope="row">{jourCourt.format(new Date(j.jour))}</th><td className="nombre">{j.questions}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </section>

            <section className="admin-panneau" aria-labelledby="titre-issues">
              <h2 id="titre-issues" className="sous-titre">Issues du moteur</h2>
              <ul className="admin-issues">
                {(Object.keys(ISSUES) as (keyof typeof ISSUES)[]).map((k) => {
                  const part = totalIssues ? t.issues[k] / totalIssues : 0;
                  return (
                    <li key={k} className={`issue-${k}`}>
                      <span>{ISSUES[k]}</span>
                      <strong>{pourcent.format(part)}</strong>
                      <span className="admin-jauge" aria-hidden="true"><span style={{ width: `${part * 100}%` }} /></span>
                      <span className="note">{entier.format(t.issues[k])} questions</span>
                    </li>
                  );
                })}
              </ul>
            </section>
          </div>

          <section className="admin-panneau" aria-labelledby="titre-non-resolues">
            <div className="admin-titre">
              <h2 id="titre-non-resolues" className="sous-titre">Questions non résolues les plus fréquentes</h2>
              <Link href="/admin/journal" className="lien">Tout voir dans le journal</Link>
            </div>
            {t.non_resolues.length === 0 ? (
              <p className="note">Aucun refus sur la période.</p>
            ) : (
              <div className="tableau-defile admin-table" role="region" aria-label="Questions non résolues" tabIndex={0}>
                <table className="tableau">
                  <thead>
                    <tr>
                      <th scope="col">Question</th>
                      <th scope="col">Langue</th>
                      <th scope="col">Motif</th>
                      <th scope="col" className="nombre">Occurrences</th>
                    </tr>
                  </thead>
                  <tbody>
                    {t.non_resolues.map((q) => (
                      <tr key={q.question}>
                        <th scope="row" lang={q.langue === "wo" ? "wo" : undefined}>{q.question}</th>
                        <td>{q.langue.toUpperCase()}</td>
                        <td>{MOTIFS[q.motif] ?? q.motif}</td>
                        <td className="nombre">{q.occurrences}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </Cadre>
  );
}
