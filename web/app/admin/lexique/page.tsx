"use client";

import { useCallback, useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { appelAdmin, Cadre, Connexion, useAdmin } from "@/components/Admin";
import { Telecharger } from "@/components/icones";

/**
 * Lexique grand public et wolof (back-office, route /admin/lexique, #23). Une expression des usagers
 * (« les mamans ») et ce que le moteur comprend (« les femmes ») : proposée, puis validée (elle réécrit alors la
 * question avant le moteur, sans déploiement) ou rejetée. Le wolof est proposé et validé par le linguiste
 * (décision 0009). « Essayer » montre la réécriture sans appeler le moteur ; l'export CSV sert à l'intégrer au
 * moteur ensuite.
 */
type Statut = "propose" | "valide" | "rejete";
type Entree = {
  id: string;
  expression: string;
  remplacement: string;
  langue: "fr" | "wo";
  statut: Statut;
  note: string | null;
  propose_par: string;
  propose_le: string;
  decide_par: string | null;
  decide_le: string | null;
  utilisations: number;
};

const STATUTS: Record<Statut, string> = { propose: "Proposées", valide: "Validées", rejete: "Rejetées" };
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short" });

export default function Lexique() {
  const { identifiant, role, avis, connecter, fermer, appeler } = useAdmin();
  const [statut, setStatut] = useState<Statut>("propose");
  const [donnees, setDonnees] = useState<{ comptes: Record<Statut, number>; entrees: Entree[] } | null>(null);
  const [nouvelle, setNouvelle] = useState({ expression: "", remplacement: "", langue: "fr", note: "" });
  const [essai, setEssai] = useState("");
  const [resultat, setResultat] = useState<{ transformee: string; appliquees: { expression: string }[] } | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; texte: string } | null>(null);

  const charger = useCallback(() => {
    appeler(`/admin/lexique?statut=${statut}`)
      .then((r) => r.json())
      .then(setDonnees)
      .catch((e: Error) => setMessage({ ok: false, texte: e.message }));
  }, [appeler, statut]);

  useEffect(() => {
    if (identifiant) charger();
  }, [identifiant, charger]);

  async function envoyer(chemin: string, corps: object) {
    const r = await appelAdmin(chemin, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps),
    }).catch(() => null);
    const p = r && !r.ok ? await r.json().catch(() => null) : null;
    return { ok: !!r?.ok, reponse: r, probleme: p as { title: string; detail?: string } | null };
  }

  async function proposer(e: React.FormEvent) {
    e.preventDefault();
    const { ok, probleme } = await envoyer("/admin/lexique", { ...nouvelle, note: nouvelle.note || null });
    setMessage(ok ? { ok: true, texte: `« ${nouvelle.expression} » proposée : elle s'appliquera une fois validée.` }
      : { ok: false, texte: probleme ? `${probleme.title}${probleme.detail ? ` : ${probleme.detail}` : ""}` : "L'API ne répond pas." });
    if (ok) setNouvelle({ expression: "", remplacement: "", langue: nouvelle.langue, note: "" });
    charger();
  }

  async function decider(entree: Entree, s: Statut) {
    const { ok } = await envoyer(`/admin/lexique/${entree.id}/statut`, { statut: s });
    setMessage(ok ? { ok: true, texte: `« ${entree.expression} » : ${STATUTS[s].toLowerCase().replace(/s$/, "")}.` }
      : { ok: false, texte: "La décision n'a pas pu être enregistrée." });
    charger();
  }

  async function essayer(e: React.FormEvent) {
    e.preventDefault();
    const { ok, reponse } = await envoyer("/admin/lexique/essai", { question: essai });
    setResultat(ok && reponse ? await reponse.json() : null);
  }

  if (!identifiant) {
    return (
      <Cadre actif="lexique">
        <Connexion erreur={avis} verification={identifiant === undefined} onConnecter={connecter} />
      </Cadre>
    );
  }

  return (
    <Cadre actif="lexique" identifiant={identifiant} role={role} onFermer={() => { fermer(); setDonnees(null); }}>
      <div className="admin-titre">
        <h1 className="titre-etat">Lexique grand public et wolof</h1>
        <a className="secondaire petit" href={`${API_URL}/admin/lexique.csv`}><Telecharger />Exporter le lexique</a>
      </div>
      <p className="aide">
        Une entrée validée réécrit la question avant le moteur (« les mamans » devient « les femmes ») ; l&apos;usager voit
        toujours sa question. Mots entiers, sans casse ni accents ; l&apos;expression la plus longue l&apos;emporte.
      </p>

      <form className="admin-panneau lexique-formulaire" onSubmit={proposer} aria-labelledby="titre-proposer">
        <h2 id="titre-proposer" className="sous-titre">Proposer une expression</h2>
        <div className="lexique-champs">
          <label className="admin-champ">
            <span>Expression des usagers</span>
            <input value={nouvelle.expression} onChange={(e) => setNouvelle({ ...nouvelle, expression: e.target.value })} maxLength={80} required placeholder="les mamans" />
          </label>
          <label className="admin-champ">
            <span>Ce que le moteur comprend</span>
            <input value={nouvelle.remplacement} onChange={(e) => setNouvelle({ ...nouvelle, remplacement: e.target.value })} maxLength={120} required placeholder="les femmes" />
          </label>
          <label className="admin-champ">
            <span>Langue</span>
            <select value={nouvelle.langue} onChange={(e) => setNouvelle({ ...nouvelle, langue: e.target.value })}>
              <option value="fr">Français</option>
              <option value="wo">Wolof (validé par le linguiste)</option>
            </select>
          </label>
          <label className="admin-champ">
            <span>Note (facultative)</span>
            <input value={nouvelle.note} onChange={(e) => setNouvelle({ ...nouvelle, note: e.target.value })} maxLength={300} placeholder="vu dans le test grand public (#280)" />
          </label>
        </div>
        <button type="submit" className="primaire petit">Proposer</button>
      </form>

      <form className="admin-panneau lexique-formulaire" onSubmit={essayer} aria-labelledby="titre-essai">
        <h2 id="titre-essai" className="sous-titre">Essayer une question</h2>
        <div className="admin-filtres">
          <label htmlFor="lexique-essai" className="sr-only">Question à essayer</label>
          <input id="lexique-essai" type="search" value={essai} onChange={(e) => setEssai(e.target.value)} maxLength={300} placeholder="Et pour les mamans ?" />
          <button type="submit" className="secondaire petit" disabled={!essai.trim()}>Essayer</button>
        </div>
        {resultat && (
          <p role="status">
            {resultat.appliquees.length === 0 ? "Aucune entrée validée ne s'applique." : <>Le moteur recevrait : <strong>« {resultat.transformee} »</strong></>}
          </p>
        )}
      </form>

      {message && <p className={message.ok ? "bandeau-discret" : "erreur-admin"} role={message.ok ? "status" : "alert"}>{message.texte}</p>}

      <div role="group" aria-label="Statut" className="bascule admin-periode lexique-statuts">
        {(Object.keys(STATUTS) as Statut[]).map((s) => (
          <button key={s} type="button" aria-pressed={statut === s} onClick={() => setStatut(s)}>
            {STATUTS[s]} ({donnees?.comptes[s] ?? 0})
          </button>
        ))}
      </div>

      <div className="tableau-defile admin-table" role="region" aria-label="Entrées du lexique" tabIndex={0}>
        <table className="tableau">
          <thead>
            <tr>
              <th scope="col">Expression</th>
              <th scope="col">Comprise comme</th>
              <th scope="col">Langue</th>
              <th scope="col">Proposée</th>
              <th scope="col" className="nombre">Utilisations</th>
              <th scope="col"><span className="sr-only">Décision</span></th>
            </tr>
          </thead>
          <tbody>
            {donnees?.entrees.length === 0 && <tr><td colSpan={6}>Aucune entrée {STATUTS[statut].toLowerCase()}.</td></tr>}
            {donnees?.entrees.map((e) => (
              <tr key={e.id}>
                <th scope="row" lang={e.langue === "wo" ? "wo" : undefined}>{e.expression}{e.note && <small className="lexique-note">{e.note}</small>}</th>
                <td>{e.remplacement}</td>
                <td>{e.langue.toUpperCase()}</td>
                <td className="admin-heure">{date.format(new Date(e.propose_le))} · {e.propose_par}{e.decide_par ? ` · décidé par ${e.decide_par}` : ""}</td>
                <td className="nombre">{e.utilisations}</td>
                <td className="lexique-actions">
                  {e.statut !== "valide" && <button type="button" className="lien-bouton" onClick={() => decider(e, "valide")}>Valider</button>}
                  {e.statut !== "rejete" && <button type="button" className="lien-bouton" onClick={() => decider(e, "rejete")}>Rejeter</button>}
                  {e.statut !== "propose" && <button type="button" className="lien-bouton" onClick={() => decider(e, "propose")}>Remettre en proposition</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Cadre>
  );
}
