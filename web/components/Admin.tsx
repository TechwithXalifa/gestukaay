"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { Baobab } from "./icones";

/**
 * Pièces communes du back-office (journal, tableau de bord). Réservé à l'équipe, en français
 * seulement : ces textes ne passent pas par i18n. Le jeton (GESTUKAAY_ADMIN_JETON) reste dans
 * l'onglet (sessionStorage), jamais ailleurs.
 */

const CLE_JETON = "gestukaay.admin";

export const CANAUX: Record<string, string> = { web: "Web", whatsapp: "WhatsApp", telegram: "Telegram", api: "API" };

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

/** Jeton de l'onglet et appel authentifié à l'API ; un jeton refusé ramène à l'écran de connexion. */
export function useAdmin() {
  const [jeton, setJeton] = useState("");
  useEffect(() => setJeton(lireJeton()), []);

  const ouvrir = useCallback((j: string) => {
    garderJeton(j);
    setJeton(j);
  }, []);
  const fermer = useCallback(() => ouvrir(""), [ouvrir]);

  const appeler = useCallback(
    async (chemin: string) => {
      const r = await fetch(`${API_URL}${chemin}`, { headers: { Authorization: `Bearer ${jeton}` } });
      if (r.status === 401) {
        fermer();
        throw new Error("Jeton refusé.");
      }
      if (r.status === 404) throw new Error("Back-office fermé : GESTUKAAY_ADMIN_JETON n'est pas configuré sur l'API.");
      if (!r.ok) throw new Error("L'API ne répond pas.");
      return r;
    },
    [jeton, fermer],
  );

  return { jeton, ouvrir, fermer, appeler };
}

export function Connexion({ titre, bouton, erreur, onOuvrir }: {
  titre: string;
  bouton: string;
  erreur: string | null;
  onOuvrir: (jeton: string) => void;
}) {
  const [saisie, setSaisie] = useState("");
  return (
    <form
      className="admin-connexion"
      onSubmit={(e) => {
        e.preventDefault();
        onOuvrir(saisie.trim());
        setSaisie("");
      }}
    >
      <h1 className="titre-etat">{titre}</h1>
      <label htmlFor="jeton">Jeton d'administration</label>
      <input id="jeton" type="password" autoComplete="off" value={saisie} onChange={(e) => setSaisie(e.target.value)} required />
      <p className="note">Valeur de GESTUKAAY_ADMIN_JETON. Elle reste dans cet onglet et disparaît à sa fermeture.</p>
      {erreur && <p className="erreur-admin" role="alert">{erreur}</p>}
      <button type="submit" className="primaire">{bouton}</button>
    </form>
  );
}

export function Cadre({ children, actif, onFermer }: {
  children: React.ReactNode;
  actif: "tableau" | "journal";
  onFermer?: () => void;
}) {
  return (
    <div className="site admin">
      <header className="admin-entete">
        <Link href="/" className="logo"><Baobab /> <span>Gëstukaay</span></Link>
        <span className="admin-pastille">Admin</span>
        <nav aria-label="Back-office" className="admin-nav">
          <Link href="/admin/tableau" aria-current={actif === "tableau" ? "page" : undefined}>Tableau de bord</Link>
          <Link href="/admin/journal" aria-current={actif === "journal" ? "page" : undefined}>Journal des requêtes</Link>
        </nav>
        {onFermer && (
          <div className="admin-actions">
            <button type="button" className="secondaire petit" onClick={onFermer}>Fermer la session</button>
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
