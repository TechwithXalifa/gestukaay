"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { appelAdmin, CANAUX, Cadre, Choix, Connexion, useAdmin } from "@/components/Admin";
import { Telecharger } from "@/components/icones";
import { nombre } from "@/lib/typo";

/**
 * Back-office minimal : journal des requêtes (maquette BO-Journal, backend #73).
 * Réservé à l'équipe ; connexion et cadre communs dans components/Admin.tsx.
 */

type Ligne = {
  recu_le: string;
  canal: string;
  source: string;
  langue: string;
  question: string;
  transcription_brute: string | null;
  issue: "exacte" | "approchee" | "aucune";
  indicateur: string | null;
  latence_ms: number | null;
  version_socle: string;
  conversation: string | null;
  confirme_depuis: string | null;
  reponse_id: string;
  vote: "utile" | "pas_utile" | null;
  signalement: string | null;
  commentaire: string | null; // texte libre laissé avec le signalement
  suggestions: number; // EF-51 : indicateur manquant suggéré depuis le refus
  suggestion: string | null; // texte de la dernière suggestion
};

type Resume = { issue: Ligne["issue"]; indicateur: string | null; version_socle: string; texte: string[]; motif?: string };
type Rejeu = { avant: Resume & { le: string }; apres: Resume & { latence_ms: number }; identique: boolean };

const PAR_PAGE = 50;
const ISSUES = { exacte: "Exacte", approchee: "Approchée", aucune: "Refus" } as const;
const RETOURS = { signale: "Signalée", pas_utile: "Jugée pas utile", utile: "Jugée utile", suggere: "Indicateur suggéré" } as const;
const MOTIFS: Record<string, string> = {
  chiffre_faux: "chiffre faux",
  mauvaise_zone: "mauvaise zone",
  mauvaise_comprehension: "question mal comprise",
  autre: "autre",
};
const LENTE_MS = 3000; // 7.6 : au-delà, la requête est signalée

const heure = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "medium" });
function secondes(ms: number | null): string {
  if (ms === null) return "–";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} s`;
}

export default function Journal() {
  const { identifiant, role, avis, connecter, fermer, appeler } = useAdmin();
  const [filtres, setFiltres] = useState({ canal: "", issue: "", retour: "", q: "" });
  const [recherche, setRecherche] = useState("");
  const [page, setPage] = useState(0);
  const [donnees, setDonnees] = useState<{ total: number; lignes: Ligne[] } | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [choisie, setChoisie] = useState<Ligne | null>(null);
  // Rejeu de la requête choisie sur le moteur actuel (rien n'est enregistré)
  const [rejeu, setRejeu] = useState<Rejeu | "en_cours" | "erreur" | null>(null);
  useEffect(() => setRejeu(null), [choisie]);

  async function rejouer(rid: string) {
    setRejeu("en_cours");
    const r = await appelAdmin("/admin/rejouer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reponse_id: rid }),
    }).catch(() => null);
    setRejeu(r?.ok ? await r.json() : "erreur");
  }

  const parametres = useCallback(
    (extra: Record<string, string> = {}) => {
      const p = new URLSearchParams(extra);
      for (const [k, v] of Object.entries(filtres)) if (v) p.set(k, v);
      return p;
    },
    [filtres],
  );

  useEffect(() => {
    if (!identifiant) return;
    let annule = false;
    const p = parametres({ limite: String(PAR_PAGE), decalage: String(page * PAR_PAGE) });
    appeler(`/admin/journal?${p}`)
      .then((r) => r.json())
      .then((d) => {
        if (!annule) {
          setDonnees(d);
          setErreur(null);
        }
      })
      .catch((e: Error) => !annule && setErreur(e.message));
    return () => {
      annule = true;
    };
  }, [identifiant, page, parametres, appeler]);

  async function exporter() {
    try {
      const r = await appeler(`/admin/journal.csv?${parametres()}`);
      const url = URL.createObjectURL(await r.blob());
      const a = Object.assign(document.createElement("a"), { href: url, download: "gestukaay-journal.csv" });
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErreur((e as Error).message);
    }
  }

  function filtrer(cle: keyof typeof filtres, valeur: string) {
    setFiltres((f) => ({ ...f, [cle]: valeur }));
    setPage(0);
    setChoisie(null);
  }

  if (!identifiant) {
    return (
      <Cadre actif="journal">
        <Connexion erreur={avis ?? erreur} verification={identifiant === undefined} onConnecter={connecter} />
      </Cadre>
    );
  }

  const debut = donnees && donnees.total ? page * PAR_PAGE + 1 : 0;
  const fin = donnees ? Math.min((page + 1) * PAR_PAGE, donnees.total) : 0;

  return (
    <Cadre actif="journal" identifiant={identifiant} role={role} onFermer={() => { fermer(); setDonnees(null); }}>
      <div className="admin-titre">
        <div>
          <h1 className="titre-etat">Journal des requêtes</h1>
          <p className="note">
            {donnees ? `${nombre(donnees.total)} requêtes` : "Chargement…"} · aucune donnée personnelle :
            chaque conversation n'est connue que par un code haché
          </p>
        </div>
        <button type="button" className="secondaire petit" onClick={exporter}>
          <Telecharger taille={16} /> Exporter CSV
        </button>
      </div>

      <form
        className="admin-filtres"
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          filtrer("q", recherche.trim());
        }}
      >
        <label className="sr-only" htmlFor="recherche">Rechercher dans le journal</label>
        <input id="recherche" type="search" placeholder="Rechercher une question" value={recherche} onChange={(e) => setRecherche(e.target.value)} />
        <Choix libelle="Canal" valeur={filtres.canal} onChange={(v) => filtrer("canal", v)} options={CANAUX} tous="tous" />
        <Choix libelle="Issue" valeur={filtres.issue} onChange={(v) => filtrer("issue", v)} options={ISSUES} tous="toutes" />
        <Choix libelle="Retour" valeur={filtres.retour} onChange={(v) => filtrer("retour", v)} options={RETOURS} tous="tous" />
      </form>

      {erreur && <p className="erreur-admin" role="alert">{erreur}</p>}

      <div className="admin-corps">
        <div className="tableau-defile admin-table" role="region" aria-label="Requêtes" tabIndex={0}>
          <table className="tableau">
            <thead>
              <tr>
                <th scope="col">Heure</th>
                <th scope="col">Canal</th>
                <th scope="col">Question ou transcription</th>
                <th scope="col">Issue</th>
                <th scope="col" className="nombre">Latence</th>
                <th scope="col">Retour</th>
              </tr>
            </thead>
            <tbody>
              {donnees?.lignes.map((l) => (
                <tr key={l.reponse_id} className={choisie?.reponse_id === l.reponse_id ? "en-evidence" : undefined}>
                  <td className="admin-heure">{heure.format(new Date(l.recu_le))}</td>
                  <td>{[CANAUX[l.canal] ?? l.canal, l.source === "voix" && "vocal", l.langue.toUpperCase()].filter(Boolean).join(" · ")}</td>
                  <th scope="row">
                    <button type="button" className="lien-bouton admin-question" onClick={() => setChoisie(l)}>
                      <span lang={l.langue === "wo" ? "wo" : undefined}>{l.question}</span>
                    </button>
                  </th>
                  <td><span className={`badge ${l.issue === "exacte" ? "exacte" : l.issue === "approchee" ? "approchee" : "projection"}`}>{ISSUES[l.issue]}</span></td>
                  <td className={`nombre${(l.latence_ms ?? 0) > LENTE_MS ? " lente" : ""}`}>{secondes(l.latence_ms)}</td>
                  <td>{[l.vote === "utile" ? "utile" : l.vote === "pas_utile" ? "pas utile" : null, l.signalement && "signalé", l.suggestions > 0 && "suggéré"].filter(Boolean).join(" · ") || "–"}</td>
                </tr>
              ))}
              {donnees && donnees.lignes.length === 0 && (
                <tr><td colSpan={6} className="note">Aucune requête pour ces filtres.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {choisie && (
          <aside className="bloc-source admin-detail" aria-label="Détail de la requête">
            <p className="bloc-source-titre">Requête du {heure.format(new Date(choisie.recu_le))}</p>
            <dl>
              <dt>Question</dt><dd lang={choisie.langue === "wo" ? "wo" : undefined}>{choisie.question}</dd>
              {choisie.transcription_brute && (<><dt>Transcription brute</dt><dd>{choisie.transcription_brute}</dd></>)}
              <dt>Issue</dt><dd>{ISSUES[choisie.issue]} · {secondes(choisie.latence_ms)}</dd>
              <dt>Indicateur</dt><dd>{choisie.indicateur ?? "aucun"}</dd>
              <dt>Socle</dt><dd>{choisie.version_socle}</dd>
              <dt>Conversation</dt><dd>{choisie.conversation ? `${choisie.conversation} (hachée)` : "aucune"}</dd>
              {choisie.confirme_depuis && (<><dt>Choix confirmé depuis</dt><dd>{choisie.confirme_depuis}</dd></>)}
              <dt>Retour</dt>
              <dd>
                {choisie.vote === "utile" ? "Jugée utile" : choisie.vote === "pas_utile" ? "Jugée pas utile" : "Pas de vote"}
                {" · "}
                {choisie.signalement ? `signalement : ${MOTIFS[choisie.signalement] ?? choisie.signalement}` : "aucun signalement"}
              </dd>
              {choisie.commentaire && (<><dt>Commentaire de l&apos;usager</dt><dd className="admin-commentaire">{choisie.commentaire}</dd></>)}
              {choisie.suggestion && (<><dt>Indicateur suggéré</dt><dd className="admin-commentaire">{choisie.suggestion}</dd></>)}
            </dl>
            <Link href={`/r/${choisie.reponse_id}`} className="lien" target="_blank">Voir la réponse</Link>
            <section className="admin-rejeu" aria-label="Rejouer sur le moteur actuel">
              <button type="button" className="secondaire petit" disabled={rejeu === "en_cours"} onClick={() => rejouer(choisie.reponse_id)}>
                {rejeu === "en_cours" ? "Rejeu en cours…" : "Rejouer sur le moteur actuel"}
              </button>
              <p className="note">Même question, moteur et socle d&apos;aujourd&apos;hui, sans le contexte de la conversation. Rien n&apos;est enregistré.</p>
              {rejeu === "erreur" && <p className="erreur-admin" role="alert">Le rejeu a échoué.</p>}
              {rejeu && typeof rejeu === "object" && (
                <div role="status">
                  <p><span className={rejeu.identique ? "badge exacte" : "badge approchee"}>{rejeu.identique ? "Réponse identique" : "Réponse différente"}</span></p>
                  {(["avant", "apres"] as const).map((quand) => {
                    const r = rejeu[quand];
                    return (
                      <div key={quand} className="admin-rejeu-cote">
                        <p className="admin-tuile-titre">{quand === "avant" ? `Avant (socle ${r.version_socle})` : `Maintenant (socle ${r.version_socle})`}</p>
                        <p>{ISSUES[r.issue]}{r.motif ? ` · ${r.motif}` : ""}{r.indicateur ? ` · ${r.indicateur}` : ""}</p>
                        <ul>{r.texte.map((t) => <li key={t}>{t}</li>)}</ul>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
            <button type="button" className="lien-bouton" onClick={() => setChoisie(null)}>Fermer le détail</button>
          </aside>
        )}
      </div>

      {donnees && donnees.total > 0 && (
        <nav className="admin-pages" aria-label="Pages du journal">
          <span className="note">{debut} à {fin} sur {nombre(donnees.total)}</span>
          <button type="button" className="secondaire petit" disabled={page === 0} onClick={() => setPage(page - 1)}>Précédentes</button>
          <button type="button" className="secondaire petit" disabled={fin >= donnees.total} onClick={() => setPage(page + 1)}>Suivantes</button>
        </nav>
      )}
    </Cadre>
  );
}
