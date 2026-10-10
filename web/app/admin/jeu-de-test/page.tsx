"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Cadre, Connexion, appelAdmin, useAdmin } from "@/components/Admin";

/**
 * Jeu de test du back-office (cahier 5.10, maquette BO-JeuTest). Lance le benchmark de KBD
 * (mesure/scripts/benchmark.py) par l'API et compare deux exécutions question par question :
 * régressions, questions corrigées, échecs. Réservé à l'équipe, en français seulement.
 */

type Resume = {
  mode: string;
  nb_total: number;
  nb_reponses_attendues: number;
  nb_exactitude_succes: number;
  score_exactitude: number;
  nb_refus_attendus: number;
  nb_refus_succes: number;
  score_refus: number;
  nb_chiffres_faux_affiches: number;
  nb_violations_invariant: number;
  latence_mediane_ms: number;
  latence_p95_ms: number;
};
type Execution = { id: string; mode: string; lancee_le: string; statut: "en_cours" | "terminee" | "echec"; erreur: string | null; resume: Resume | null };
type Question = { id: string; question: string; type: string; langue: string; issue_attendue: string };
type Evaluation = { question_id: string; issue_obtenue: string; reponse_correcte: boolean; chiffre_faux: boolean; statut: string; detail: string };
type Liste = { disponible: boolean; llm_autorise: boolean; questions: Question[]; executions: Execution[] };

const MODES: Record<string, string> = { regles: "règles locales", llm: "LLM" };
const ISSUES: Record<string, string> = { exacte: "exacte", approchee: "approchée", aucune: "refus" };
const heure = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" });
const pc = (x: number) => `${(x * 100).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %`;
const sec = (ms: number) =>
  ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} s`;
const nomMode = (m: string) => (m.startsWith("llm") ? `LLM (${m.replace(/^llm-?/, "") || "chaîne du .env"})` : MODES[m] ?? m);

function libelleExecution(e: Execution): string {
  return `${heure.format(new Date(e.lancee_le))} · ${nomMode(e.resume?.mode ?? e.mode)}`;
}

export default function JeuDeTest() {
  const { identifiant, role, avis, connecter, fermer, appeler } = useAdmin();
  const [liste, setListe] = useState<Liste | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [idA, setIdA] = useState("");
  const [idB, setIdB] = useState("");
  const [evals, setEvals] = useState<Record<string, Record<string, Evaluation>>>({});
  const [onglet, setOnglet] = useState<"changements" | "echecs" | "toutes">("changements");
  const [choisie, setChoisie] = useState<string | null>(null);
  const [confirmerLlm, setConfirmerLlm] = useState(false);

  const charger = useCallback(async () => {
    try {
      const l: Liste = await (await appeler("/admin/jeu-de-test")).json();
      setListe(l);
      setErreur(null);
      const finies = l.executions.filter((e) => e.statut === "terminee");
      setIdB((b) => b || finies[0]?.id || "");
      setIdA((a) => a || finies[1]?.id || "");
    } catch (e) {
      setErreur((e as Error).message);
    }
  }, [appeler]);

  useEffect(() => {
    if (identifiant) charger();
  }, [identifiant, charger]);

  // Une exécution en cours : on relit la liste toutes les 3 s jusqu'à sa fin
  const enCours = liste?.executions.some((e) => e.statut === "en_cours");
  useEffect(() => {
    if (!enCours) return;
    const id = setInterval(charger, 3000);
    return () => clearInterval(id);
  }, [enCours, charger]);

  // Détail des deux exécutions comparées (chargé une fois par exécution)
  useEffect(() => {
    for (const id of [idA, idB].filter((x) => x && !evals[x])) {
      appeler(`/admin/jeu-de-test/executions/${id}`)
        .then((r) => r.json())
        .then((e) => {
          const parQuestion: Record<string, Evaluation> = {};
          for (const ev of e.resultat?.evaluations ?? []) parQuestion[ev.question_id] = ev;
          setEvals((x) => ({ ...x, [id]: parQuestion }));
        })
        .catch((e: Error) => setErreur(e.message));
    }
  }, [idA, idB, evals, appeler]);

  async function lancer(mode: "regles" | "llm") {
    setConfirmerLlm(false);
    try {
      const r = await appelAdmin("/admin/jeu-de-test/executions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? "Le lancement a échoué.");
      setIdB("");
      setIdA("");
      await charger();
    } catch (e) {
      setErreur((e as Error).message);
    }
  }

  const executions = liste?.executions ?? [];
  const finies = executions.filter((e) => e.statut === "terminee");
  const exA = finies.find((e) => e.id === idA);
  const exB = finies.find((e) => e.id === idB);
  const a = idA ? evals[idA] : undefined;
  const b = idB ? evals[idB] : undefined;

  const lignes = useMemo(() => {
    if (!liste || !b) return [];
    return liste.questions
      .map((q) => ({ q, ea: a?.[q.id], eb: b[q.id] }))
      .filter(({ ea, eb }) => {
        if (onglet === "toutes") return true;
        if (onglet === "echecs") return eb && !eb.reponse_correcte;
        return a ? ea && eb && ea.reponse_correcte !== eb.reponse_correcte : eb && !eb.reponse_correcte;
      });
  }, [liste, a, b, onglet]);

  const regressions = a && b ? Object.keys(b).filter((id) => a[id]?.reponse_correcte && !b[id].reponse_correcte).length : null;
  const corrigees = a && b ? Object.keys(b).filter((id) => a[id] && !a[id].reponse_correcte && b[id].reponse_correcte).length : null;
  const echecs = b ? Object.values(b).filter((e) => !e.reponse_correcte).length : 0;
  const q = liste?.questions.find((x) => x.id === choisie);

  if (!identifiant) {
    return (
      <Cadre actif="jeu">
        <Connexion erreur={avis ?? erreur} verification={identifiant === undefined} onConnecter={connecter} />
      </Cadre>
    );
  }

  return (
    <Cadre actif="jeu" identifiant={identifiant} role={role} onFermer={() => { fermer(); setListe(null); }}>
      <div className="admin-titre">
        <div>
          <h1 className="titre-etat">Jeu de test</h1>
          <p className="note">
            {liste ? `${liste.questions.length} questions de référence` : "Chargement…"} · simples, comparatives,
            classements, approchées, refus et suivis · benchmark de mesure/scripts/benchmark.py
          </p>
        </div>
        {role === "admin" ? (
        <div className="admin-filtres">
          <button type="button" className="primaire" disabled={!liste?.disponible || enCours} onClick={() => lancer("regles")}>
            Relancer (règles locales)
          </button>
          {confirmerLlm ? (
            <>
              <button type="button" className="secondaire" onClick={() => lancer("llm")}>Confirmer : environ 0,07 $</button>
              <button type="button" className="tertiaire" onClick={() => setConfirmerLlm(false)}>Annuler</button>
            </>
          ) : (
            <button type="button" className="secondaire" disabled={!liste?.disponible || !liste?.llm_autorise || enCours}
                    onClick={() => setConfirmerLlm(true)}>
              Relancer avec le LLM
            </button>
          )}
        </div>
        ) : (
          <p className="note">Le lancement du jeu de test est réservé aux administrateurs.</p>
        )}
      </div>

      {liste && !liste.disponible && (
        <p className="bandeau-discret" role="status">
          L'API tourne sur le faux moteur : le benchmark demande le moteur réel (GESTUKAAY_MOTEUR=reel).
        </p>
      )}
      {liste?.disponible && !liste.llm_autorise && (
        <p className="note">
          Le benchmark avec le LLM est désactivé sur ce serveur (coût et moteur occupé 2 à 3 minutes) :
          GESTUKAAY_BENCHMARK_LLM=oui pour l'ouvrir, en local ou hors démo.
        </p>
      )}
      {enCours && <p className="bandeau-discret" role="status">Exécution en cours… les résultats s'affichent dès la fin.</p>}
      {executions.filter((e) => e.statut === "echec").slice(0, 1).map((e) => (
        <p key={e.id} className="erreur-admin" role="alert">Dernier échec ({heure.format(new Date(e.lancee_le))}) : {e.erreur}</p>
      ))}
      {erreur && <p className="erreur-admin" role="alert">{erreur}</p>}

      {liste && finies.length === 0 && !enCours && (
        <p className="explication">Aucune exécution pour l'instant : lancez le benchmark pour voir les résultats.</p>
      )}

      {finies.length > 0 && (
        <>
          <div className="admin-filtres">
            <label className="admin-choix">
              <span>Exécution :</span>
              <select value={idB} onChange={(e) => { setIdB(e.target.value); setChoisie(null); }}>
                {finies.map((e) => <option key={e.id} value={e.id}>{libelleExecution(e)}</option>)}
              </select>
            </label>
            <label className="admin-choix">
              <span>Comparée à :</span>
              <select value={idA} onChange={(e) => { setIdA(e.target.value); setChoisie(null); }}>
                <option value="">aucune</option>
                {finies.filter((e) => e.id !== idB).map((e) => <option key={e.id} value={e.id}>{libelleExecution(e)}</option>)}
              </select>
            </label>
          </div>

          {exB?.resume && (
            <ul className="admin-tuiles">
              <Tuile titre="Exactitude" valeur={pc(exB.resume.score_exactitude)} cible="cible ≥ 85 %"
                     ok={exB.resume.score_exactitude >= 0.85} ecart={exA?.resume && ecartPoints(exB.resume.score_exactitude, exA.resume.score_exactitude)} />
              <Tuile titre="Refus pertinents" valeur={pc(exB.resume.score_refus)} cible="cible ≥ 95 %"
                     ok={exB.resume.score_refus >= 0.95} ecart={exA?.resume && ecartPoints(exB.resume.score_refus, exA.resume.score_refus)} />
              <Tuile titre="Latence médiane" valeur={sec(exB.resume.latence_mediane_ms)} cible={`p95 : ${sec(exB.resume.latence_p95_ms)} · cible < 3 s`}
                     ok={exB.resume.latence_mediane_ms < 3000} />
              <Tuile titre="Chiffres hors sujet" valeur={String(exB.resume.nb_chiffres_faux_affiches)} cible="cible 0"
                     ok={exB.resume.nb_chiffres_faux_affiches === 0} />
              <Tuile titre="Chiffres inventés" valeur={String(exB.resume.nb_violations_invariant)} cible="invariant : 0, toujours"
                     ok={exB.resume.nb_violations_invariant === 0} />
              {regressions !== null && (
                <Tuile titre="Régressions" valeur={String(regressions)} cible={`${corrigees} question(s) corrigée(s)`} ok={regressions === 0} />
              )}
            </ul>
          )}
          {regressions !== null && regressions > 0 && (
            <p className="bandeau-discret" role="status">
              {regressions} question(s) réussie(s) dans l'exécution de comparaison échouent maintenant : à corriger avant de
              livrer une nouvelle version du moteur ou du socle.
            </p>
          )}

          <div role="group" aria-label="Questions affichées" className="bascule admin-periode">
            {([["changements", a ? "Changements" : "Échecs"], ["echecs", `Échecs (${echecs})`], ["toutes", "Toutes"]] as const).map(([k, l]) => (
              <button key={k} type="button" aria-pressed={onglet === k} onClick={() => setOnglet(k)}>{l}</button>
            ))}
          </div>

          <div className="admin-corps">
            <div className="tableau-defile admin-table" role="region" aria-label="Questions du jeu de test" tabIndex={0}>
              <table className="tableau">
                <thead>
                  <tr>
                    <th scope="col">N°</th>
                    <th scope="col">Question</th>
                    <th scope="col">Type</th>
                    {a && <th scope="col">Comparée</th>}
                    <th scope="col">Exécution</th>
                  </tr>
                </thead>
                <tbody>
                  {lignes.map(({ q, ea, eb }) => (
                    <tr key={q.id} className={choisie === q.id ? "en-evidence" : undefined}>
                      <td className="admin-heure">{q.id}</td>
                      <th scope="row">
                        <button type="button" className="lien-bouton admin-question" onClick={() => setChoisie(q.id)}>
                          <span lang={q.langue === "wo" ? "wo" : undefined}>{q.question}</span>
                        </button>
                      </th>
                      <td>{q.type} · {q.langue.toUpperCase()}</td>
                      {a && <td><Statut ev={ea} /></td>}
                      <td><Statut ev={eb} /></td>
                    </tr>
                  ))}
                  {b && lignes.length === 0 && (
                    <tr><td colSpan={a ? 5 : 4} className="note">Aucune question dans cette vue.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            {q && (
              <aside className="bloc-source admin-detail" aria-label="Détail de la question">
                <p className="bloc-source-titre">Question {q.id}</p>
                <dl>
                  <dt>Question</dt><dd lang={q.langue === "wo" ? "wo" : undefined}>{q.question}</dd>
                  <dt>Attendu</dt><dd>{ISSUES[q.issue_attendue] ?? q.issue_attendue}</dd>
                  {a && exA && (<><dt>Comparée</dt><dd>{detail(a[q.id])}</dd></>)}
                  {exB && b && (<><dt>Exécution</dt><dd>{detail(b[q.id])}</dd></>)}
                </dl>
                <button type="button" className="lien-bouton" onClick={() => setChoisie(null)}>Fermer le détail</button>
              </aside>
            )}
          </div>
        </>
      )}
    </Cadre>
  );
}

function ecartPoints(nouveau: number, ancien: number): string {
  const d = (nouveau - ancien) * 100;
  if (Math.abs(d) < 0.05) return "= par rapport à la comparée";
  return `${d > 0 ? "+" : "−"}${Math.abs(d).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} pts par rapport à la comparée`;
}

function Tuile({ titre, valeur, cible, ok, ecart }: { titre: string; valeur: string; cible: string; ok: boolean; ecart?: string | null }) {
  return (
    <li>
      <span className="admin-tuile-titre">{titre}</span>
      <strong className={ok ? undefined : "hors-cible"}>{valeur}</strong>
      <span className="note">{cible}</span>
      {ecart && <span className="note">{ecart}</span>}
    </li>
  );
}

function Statut({ ev }: { ev?: Evaluation }) {
  if (!ev) return <span className="note">–</span>;
  if (ev.reponse_correcte) return <span className="badge exacte">Réussie</span>;
  return <span className="badge approchee">{ev.chiffre_faux ? "Chiffre hors sujet" : `Échec : ${ISSUES[ev.issue_obtenue] ?? ev.issue_obtenue}`}</span>;
}

function detail(ev?: Evaluation): string {
  if (!ev) return "pas dans cette exécution";
  const issue = ISSUES[ev.issue_obtenue] ?? ev.issue_obtenue;
  return `${ev.reponse_correcte ? "réussie" : "échouée"} · ${issue}${ev.detail ? ` · ${ev.detail}` : ""}`;
}
