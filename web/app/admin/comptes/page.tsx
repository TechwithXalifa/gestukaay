"use client";

import { useCallback, useEffect, useState } from "react";
import { appelAdmin, Cadre, Connexion, ROLES, useAdmin } from "@/components/Admin";

/**
 * Comptes et rôles du back-office (route /admin/comptes, administrateurs seulement). Créer un compte nominatif
 * avec son rôle, changer un rôle, désactiver un compte, donner un nouveau mot de passe (qui le réactive). Les
 * mêmes actions existent en ligne de commande (python -m gestukaay_backend.comptes).
 */
type Compte = { identifiant: string; role: string; actif: boolean; cree_le: string };

const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });
const LONGUEUR_MIN = 12;

export default function Comptes() {
  const { identifiant, role, avis, connecter, fermer, appeler } = useAdmin();
  const [comptes, setComptes] = useState<Compte[] | null>(null);
  const [descriptions, setDescriptions] = useState<Record<string, string>>({});
  const [nouveau, setNouveau] = useState({ identifiant: "", role: "lecteur", mot_de_passe: "", confirmation: "" });
  const [message, setMessage] = useState<{ ok: boolean; texte: string } | null>(null);

  const charger = useCallback(() => {
    appeler("/admin/comptes")
      .then((r) => r.json())
      .then((d) => {
        setComptes(d.comptes);
        setDescriptions(d.roles);
      })
      .catch((e: Error) => setMessage({ ok: false, texte: e.message }));
  }, [appeler]);

  useEffect(() => {
    if (identifiant && role === "admin") charger();
  }, [identifiant, role, charger]);

  async function envoyer(chemin: string, corps: object | null, reussite: string) {
    const r = await appelAdmin(chemin, {
      method: "POST",
      headers: corps ? { "Content-Type": "application/json" } : undefined,
      body: corps ? JSON.stringify(corps) : undefined,
    }).catch(() => null);
    if (r?.ok) setMessage({ ok: true, texte: reussite });
    else {
      const p = await r?.json().catch(() => null);
      setMessage({ ok: false, texte: p ? `${p.title}${p.detail ? ` : ${p.detail}` : ""}` : "L'API ne répond pas." });
    }
    charger();
    return !!r?.ok;
  }

  async function creer(e: React.FormEvent) {
    e.preventDefault();
    if (nouveau.mot_de_passe !== nouveau.confirmation) {
      setMessage({ ok: false, texte: "Les deux mots de passe diffèrent." });
      return;
    }
    const { confirmation: _, ...corps } = nouveau;
    if (await envoyer("/admin/comptes", corps, `Compte ${nouveau.identifiant} créé.`))
      setNouveau({ identifiant: "", role: "lecteur", mot_de_passe: "", confirmation: "" });
  }

  async function motDePasse(c: Compte) {
    const mdp = window.prompt(`Nouveau mot de passe pour ${c.identifiant} (${LONGUEUR_MIN} caractères au moins). Ses sessions seront fermées.`);
    if (mdp) await envoyer(`/admin/comptes/${encodeURIComponent(c.identifiant)}/mot-de-passe`, { mot_de_passe: mdp }, `Mot de passe de ${c.identifiant} changé.`);
  }

  if (!identifiant) {
    return (
      <Cadre actif="comptes">
        <Connexion erreur={avis} verification={identifiant === undefined} onConnecter={connecter} />
      </Cadre>
    );
  }

  return (
    <Cadre actif="comptes" identifiant={identifiant} role={role} onFermer={() => { fermer(); setComptes(null); }}>
      <div className="admin-titre">
        <h1 className="titre-etat">Comptes et rôles</h1>
      </div>
      {role !== "admin" ? (
        <p className="erreur-admin" role="alert">Cet écran est réservé aux administrateurs.</p>
      ) : (
        <>
          <ul className="admin-roles">
            {Object.entries(descriptions).map(([r, d]) => <li key={r}>{d}</li>)}
          </ul>
          {message && <p className={message.ok ? "bandeau-discret" : "erreur-admin"} role={message.ok ? "status" : "alert"}>{message.texte}</p>}

          <div className="tableau-defile admin-table" role="region" aria-label="Comptes du back-office" tabIndex={0}>
            <table className="tableau">
              <thead>
                <tr>
                  <th scope="col">Identifiant</th>
                  <th scope="col">Rôle</th>
                  <th scope="col">État</th>
                  <th scope="col">Créé le</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {comptes?.map((c) => (
                  <tr key={c.identifiant}>
                    <th scope="row">{c.identifiant}{c.identifiant === identifiant ? " (vous)" : ""}</th>
                    <td>
                      <select
                        aria-label={`Rôle de ${c.identifiant}`}
                        value={c.role}
                        onChange={(e) => envoyer(`/admin/comptes/${encodeURIComponent(c.identifiant)}/role`, { role: e.target.value }, `${c.identifiant} est maintenant ${ROLES[e.target.value]}.`)}
                      >
                        {Object.keys(ROLES).map((r) => <option key={r} value={r}>{ROLES[r]}</option>)}
                      </select>
                    </td>
                    <td><span className={c.actif ? "badge exacte" : "badge"}>{c.actif ? "Actif" : "Désactivé"}</span></td>
                    <td className="admin-heure">{date.format(new Date(c.cree_le))}</td>
                    <td className="admin-actions-ligne">
                      <button type="button" className="lien-bouton" onClick={() => motDePasse(c)}>{c.actif ? "Nouveau mot de passe" : "Réactiver"}</button>
                      {c.actif && c.identifiant !== identifiant && (
                        <button
                          type="button"
                          className="lien-bouton"
                          onClick={() => window.confirm(`Désactiver ${c.identifiant} ? Ses sessions seront fermées.`) &&
                            envoyer(`/admin/comptes/${encodeURIComponent(c.identifiant)}/desactiver`, null, `${c.identifiant} désactivé.`)}
                        >
                          Désactiver
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <form className="admin-panneau admin-nouveau-compte" onSubmit={creer} aria-labelledby="titre-nouveau-compte">
            <h2 id="titre-nouveau-compte" className="sous-titre">Créer un compte</h2>
            <div className="admin-champs">
              <label className="admin-champ">
                <span>Identifiant</span>
                <input value={nouveau.identifiant} onChange={(e) => setNouveau({ ...nouveau, identifiant: e.target.value })}
                       autoComplete="off" autoCapitalize="none" spellCheck={false} maxLength={32} required />
              </label>
              <label className="admin-champ">
                <span>Rôle</span>
                <select value={nouveau.role} onChange={(e) => setNouveau({ ...nouveau, role: e.target.value })}>
                  {Object.keys(ROLES).map((r) => <option key={r} value={r}>{ROLES[r]}</option>)}
                </select>
              </label>
              <label className="admin-champ">
                <span>Mot de passe ({LONGUEUR_MIN} caractères au moins)</span>
                <input type="password" value={nouveau.mot_de_passe} onChange={(e) => setNouveau({ ...nouveau, mot_de_passe: e.target.value })}
                       autoComplete="new-password" minLength={LONGUEUR_MIN} required />
              </label>
              <label className="admin-champ">
                <span>Le même, encore une fois</span>
                <input type="password" value={nouveau.confirmation} onChange={(e) => setNouveau({ ...nouveau, confirmation: e.target.value })}
                       autoComplete="new-password" minLength={LONGUEUR_MIN} required />
              </label>
            </div>
            <button type="submit" className="primaire petit">Créer le compte</button>
            <p className="note">Transmettez le mot de passe en personne, jamais par un message écrit.</p>
          </form>
        </>
      )}
    </Cadre>
  );
}
