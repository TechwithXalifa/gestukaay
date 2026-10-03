"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Baobab, Telecharger } from "@/components/icones";
import { API_URL } from "@/lib/api";

/**
 * Back-office minimal : journal des requêtes (maquette BO-Journal, backend #73).
 * Réservé à l'équipe, en français seulement : ces textes ne passent pas par i18n.
 * Le jeton (GESTUKAAY_ADMIN_JETON) reste dans l'onglet (sessionStorage), jamais ailleurs.
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
  suggestions: number; // EF-51 : indicateur manquant suggéré depuis le refus
};

const PAR_PAGE = 50;
const CLE_JETON = "gestukaay.admin";
const CANAUX: Record<string, string> = { web: "Web", whatsapp: "WhatsApp", telegram: "Telegram", api: "API" };
const ISSUES = { exacte: "Exacte", approchee: "Approchée", aucune: "Refus" } as const;
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

function lireJeton(): string {
  try {
    return sessionStorage.getItem(CLE_JETON) ?? "";
  } catch {
    return "";
  }
}

function garderJeton(jeton: string) {
  try {
    if (jeton) sessionStorage.setItem(CLE_JETON, jeton);
    else sessionStorage.removeItem(CLE_JETON);
  } catch {
    /* navigation privée : le jeton vit seulement en mémoire */
  }
}

export default function Journal() {
  const [jeton, setJeton] = useState("");
  const [saisie, setSaisie] = useState("");
  const [filtres, setFiltres] = useState({ canal: "", langue: "", issue: "", q: "" });
  const [recherche, setRecherche] = useState("");
  const [page, setPage] = useState(0);
  const [donnees, setDonnees] = useState<{ total: number; lignes: Ligne[] } | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [choisie, setChoisie] = useState<Ligne | null>(null);

  useEffect(() => setJeton(lireJeton()), []);

  const parametres = useCallback(
    (extra: Record<string, string> = {}) => {
      const p = new URLSearchParams(extra);
      for (const [k, v] of Object.entries(filtres)) if (v) p.set(k, v);
      return p;
    },
    [filtres],
  );

  const appeler = useCallback(
    async (chemin: string) => {
      const r = await fetch(`${API_URL}${chemin}`, { headers: { Authorization: `Bearer ${jeton}` } });
      if (r.status === 401) {
        garderJeton("");
        setJeton("");
        throw new Error("Jeton refusé.");
      }
      if (r.status === 404) throw new Error("Back-office fermé : GESTUKAAY_ADMIN_JETON n'est pas configuré sur l'API.");
      if (!r.ok) throw new Error("L'API ne répond pas.");
      return r;
    },
    [jeton],
  );

  useEffect(() => {
    if (!jeton) return;
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
  }, [jeton, page, parametres, appeler]);

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

  if (!jeton) {
    return (
      <Cadre>
        <form
          className="admin-connexion"
          onSubmit={(e) => {
            e.preventDefault();
            garderJeton(saisie.trim());
            setJeton(saisie.trim());
            setSaisie("");
          }}
        >
          <h1 className="titre-etat">Journal des requêtes</h1>
          <label htmlFor="jeton">Jeton d'administration</label>
          <input id="jeton" type="password" autoComplete="off" value={saisie} onChange={(e) => setSaisie(e.target.value)} required />
          <p className="note">Valeur de GESTUKAAY_ADMIN_JETON. Elle reste dans cet onglet et disparaît à sa fermeture.</p>
          {erreur && <p className="erreur-admin" role="alert">{erreur}</p>}
          <button type="submit" className="primaire">Ouvrir le journal</button>
        </form>
      </Cadre>
    );
  }

  const debut = donnees && donnees.total ? page * PAR_PAGE + 1 : 0;
  const fin = donnees ? Math.min((page + 1) * PAR_PAGE, donnees.total) : 0;

  return (
    <Cadre
      actions={
        <button type="button" className="secondaire petit" onClick={() => { garderJeton(""); setJeton(""); setDonnees(null); }}>
          Fermer la session
        </button>
      }
    >
      <div className="admin-titre">
        <div>
          <h1 className="titre-etat">Journal des requêtes</h1>
          <p className="note">
            {donnees ? `${donnees.total.toLocaleString("fr-FR")} requêtes` : "Chargement…"} · aucune donnée personnelle :
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
        <Choix libelle="Langue" valeur={filtres.langue} onChange={(v) => filtrer("langue", v)} options={{ fr: "FR", wo: "WO" }} tous="toutes" />
        <Choix libelle="Issue" valeur={filtres.issue} onChange={(v) => filtrer("issue", v)} options={ISSUES} tous="toutes" />
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
            </dl>
            <Link href={`/r/${choisie.reponse_id}`} className="lien" target="_blank">Voir la réponse</Link>
            <button type="button" className="lien-bouton" onClick={() => setChoisie(null)}>Fermer le détail</button>
          </aside>
        )}
      </div>

      {donnees && donnees.total > 0 && (
        <nav className="admin-pages" aria-label="Pages du journal">
          <span className="note">{debut} à {fin} sur {donnees.total.toLocaleString("fr-FR")}</span>
          <button type="button" className="secondaire petit" disabled={page === 0} onClick={() => setPage(page - 1)}>Précédentes</button>
          <button type="button" className="secondaire petit" disabled={fin >= donnees.total} onClick={() => setPage(page + 1)}>Suivantes</button>
        </nav>
      )}
    </Cadre>
  );
}

function Cadre({ children, actions }: { children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="site admin">
      <header className="admin-entete">
        <Link href="/" className="logo"><Baobab /> <span>Gëstukaay</span></Link>
        <span className="admin-pastille">Admin</span>
        <div className="admin-actions">{actions}</div>
      </header>
      <main id="contenu" tabIndex={-1} className="admin-main">{children}</main>
    </div>
  );
}

function Choix({ libelle, valeur, onChange, options, tous }: {
  libelle: string;
  valeur: string;
  onChange: (v: string) => void;
  options: Record<string, string>;
  tous: string;
}) {
  return (
    <label className="admin-choix">
      <span>{libelle} :</span>
      <select value={valeur} onChange={(e) => onChange(e.target.value)}>
        <option value="">{tous}</option>
        {Object.entries(options).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );
}
