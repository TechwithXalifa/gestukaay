"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { Baobab, Bouclier, Cadenas } from "./icones";

/**
 * Pièces communes du back-office (journal, tableau de bord, jeu de test). Réservé à l'équipe, en
 * français seulement : ces textes ne passent pas par i18n. Connexion par identifiant et mot de passe
 * (décision 0037) : la session vit dans un cookie HttpOnly posé par l'API, invisible pour la page.
 */

export const CANAUX: Record<string, string> = { web: "Web", whatsapp: "WhatsApp", telegram: "Telegram", api: "API" };

const FERME = "Back-office fermé : aucun compte n'est créé sur l'API (python -m gestukaay_backend.comptes).";

/** Fetch du back-office : le cookie de session part avec chaque appel. */
export function appelAdmin(chemin: string, init?: RequestInit) {
  return fetch(`${API_URL}${chemin}`, { ...init, credentials: "include" });
}

/**
 * Session du back-office. `identifiant` vaut undefined pendant la vérification, null hors connexion ;
 * `avis` dit pourquoi on ne peut pas se connecter (back-office fermé).
 * Une session refusée en cours de route (expirée, fermée ailleurs) ramène à l'écran de connexion.
 */
export function useAdmin() {
  const [identifiant, setIdentifiant] = useState<string | null | undefined>(undefined);
  const [avis, setAvis] = useState<string | null>(null);

  useEffect(() => {
    appelAdmin("/admin/moi")
      .then(async (r) => {
        if (r.status === 404) setAvis(FERME);
        setIdentifiant(r.ok ? (await r.json()).identifiant : null);
      })
      .catch(() => setIdentifiant(null));
  }, []);

  const connecter = useCallback(async (id: string, motDePasse: string) => {
    let r: Response;
    try {
      r = await appelAdmin("/admin/connexion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifiant: id, mot_de_passe: motDePasse }),
      });
    } catch {
      throw new Error("L'API ne répond pas.");
    }
    if (r.status === 404) throw new Error(FERME);
    if (r.status === 401) throw new Error("Identifiant ou mot de passe incorrect. Après 5 essais manqués, le compte est bloqué 15 minutes.");
    if (r.status === 429) throw new Error("Trop d'essais : patientez une minute.");
    if (!r.ok) throw new Error("L'API ne répond pas.");
    setIdentifiant((await r.json()).identifiant);
  }, []);

  const fermer = useCallback(() => {
    appelAdmin("/admin/deconnexion", { method: "POST" }).catch(() => {});
    setIdentifiant(null);
  }, []);

  const appeler = useCallback(async (chemin: string) => {
    const r = await appelAdmin(chemin);
    if (r.status === 401) {
      setIdentifiant(null);
      throw new Error("Session expirée : reconnectez-vous.");
    }
    if (r.status === 404) throw new Error(FERME);
    if (!r.ok) throw new Error("L'API ne répond pas.");
    return r;
  }, []);

  return { identifiant, avis, connecter, fermer, appeler };
}

/**
 * Connexion au back-office : générique, elle ne dit rien de la page visée ni de ce qu'on y trouve.
 */
export function Connexion({ erreur, verification, onConnecter }: {
  erreur: string | null;
  verification: boolean;
  onConnecter: (identifiant: string, motDePasse: string) => Promise<void>;
}) {
  const [id, setId] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [refus, setRefus] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);
  if (verification) return <p className="note admin-verification" role="status">Vérification de la session…</p>;
  const message = refus ?? erreur;
  return (
    <form
      className="admin-connexion"
      onSubmit={async (e) => {
        e.preventDefault();
        setEnvoi(true);
        try {
          await onConnecter(id.trim(), motDePasse);
        } catch (err) {
          setRefus((err as Error).message);
        } finally {
          setMotDePasse("");
          setEnvoi(false);
        }
      }}
    >
      <span className="admin-connexion-icone" aria-hidden="true"><Cadenas taille={28} /></span>
      <h1 className="titre-etat">Connexion au back-office</h1>
      <p className="admin-connexion-sous-titre">Espace réservé à l'équipe Gëstukaay.</p>
      <div className="admin-champ">
        <label htmlFor="identifiant">Identifiant</label>
        <input id="identifiant" autoComplete="username" autoCapitalize="none" spellCheck={false} value={id} onChange={(e) => setId(e.target.value)} required />
      </div>
      <div className="admin-champ">
        <label htmlFor="mot-de-passe">Mot de passe</label>
        <input id="mot-de-passe" type="password" autoComplete="current-password" value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} required />
      </div>
      {message && <p className="erreur-admin" role="alert">{message}</p>}
      <button type="submit" className="primaire" disabled={envoi}>{envoi ? "Connexion…" : "Se connecter"}</button>
      <p className="note admin-connexion-note"><Bouclier taille={16} /> Compte nominatif de l'équipe. La session se ferme après 8 h sans activité.</p>
    </form>
  );
}

export function Cadre({ children, actif, identifiant, onFermer }: {
  children: React.ReactNode;
  actif: "tableau" | "journal" | "jeu" | "signalements";
  identifiant?: string | null;
  onFermer?: () => void;
}) {
  return (
    <div className="site admin">
      <header className="admin-entete">
        <Link href="/" className="logo"><Baobab /> <span>Gëstukaay</span></Link>
        <span className="admin-pastille">Admin</span>
        {/* Les écrans du back-office ne se montrent qu'une fois connecté (onFermer n'existe qu'alors) */}
        {onFermer && (
          <nav aria-label="Back-office" className="admin-nav">
            <Link href="/admin/tableau" aria-current={actif === "tableau" ? "page" : undefined}>Tableau de bord</Link>
            <Link href="/admin/journal" aria-current={actif === "journal" ? "page" : undefined}>Journal des requêtes</Link>
            <Link href="/admin/signalements" aria-current={actif === "signalements" ? "page" : undefined}>Signalements</Link>
            <Link href="/admin/jeu-de-test" aria-current={actif === "jeu" ? "page" : undefined}>Jeu de test</Link>
          </nav>
        )}
        {onFermer && (
          <div className="admin-actions">
            {identifiant && <span className="note">{identifiant}</span>}
            <button type="button" className="secondaire petit" onClick={onFermer}>Se déconnecter</button>
          </div>
        )}
      </header>
      <main id="contenu" tabIndex={-1} className="admin-main">{children}</main>
    </div>
  );
}

export function Choix({ libelle, valeur, onChange, options, tous }: {
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
