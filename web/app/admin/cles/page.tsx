"use client";

import { useCallback, useEffect, useState } from "react";
import { appelAdmin, Cadre, Connexion, useAdmin } from "@/components/Admin";
import { Copier } from "@/components/icones";

/**
 * Clés de l'API publique (back-office, route /admin/cles). Une clé se délivre à un partenaire nommé (média,
 * administration, développeur) : elle multiplie ses limites de requêtes. Elle n'est montrée qu'une fois ; la base
 * n'en garde que l'empreinte. Une clé révoquée est refusée aussitôt (401).
 */
type Cle = { id: string; nom: string; creee_le: string; creee_par: string; active: boolean; vue_le: string | null; appels: number };

const date = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

export default function ClesApi() {
  const { identifiant, role, avis, connecter, fermer, appeler } = useAdmin();
  const [cles, setCles] = useState<Cle[] | null>(null);
  const [facteur, setFacteur] = useState(10);
  const [nom, setNom] = useState("");
  const [nouvelle, setNouvelle] = useState<{ nom: string; cle: string } | null>(null);
  const [copie, setCopie] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    appeler("/admin/cles")
      .then((r) => r.json())
      .then((d) => {
        setCles(d.cles);
        setFacteur(d.facteur);
        setErreur(null);
      })
      .catch((e: Error) => setErreur(e.message));
  }, [appeler]);

  useEffect(() => {
    if (identifiant) charger();
  }, [identifiant, charger]);

  async function delivrer(e: React.FormEvent) {
    e.preventDefault();
    const r = await appelAdmin("/admin/cles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nom: nom.trim() }),
    }).catch(() => null);
    if (!r?.ok) {
      setErreur(r?.status === 422 ? "Donnez un nom d'au moins deux caractères." : "La clé n'a pas pu être créée.");
      return;
    }
    setNouvelle({ nom: nom.trim(), cle: (await r.json()).cle });
    setCopie(false);
    setNom("");
    charger();
  }

  async function revoquer(c: Cle) {
    if (!window.confirm(`Révoquer la clé « ${c.nom} » ? Elle sera refusée aussitôt.`)) return;
    const r = await appelAdmin(`/admin/cles/${c.id}/revoquer`, { method: "POST" }).catch(() => null);
    if (!r?.ok) setErreur("La clé n'a pas pu être révoquée.");
    charger();
  }

  if (!identifiant) {
    return (
      <Cadre actif="cles">
        <Connexion erreur={avis ?? erreur} verification={identifiant === undefined} onConnecter={connecter} />
      </Cadre>
    );
  }

  return (
    <Cadre actif="cles" identifiant={identifiant} role={role} onFermer={() => { fermer(); setCles(null); }}>
      <div className="admin-titre">
        <h1 className="titre-etat">Clés de l'API publique</h1>
      </div>
      <p className="aide">
        Une clé, envoyée dans l'en-tête <code>X-Gestukaay-Cle</code>, multiplie par {facteur} les limites de requêtes de son
        détenteur. Elle n'est montrée qu'une fois : copiez-la et transmettez-la au partenaire. Documentation publique : /developpeurs.
      </p>

      <form className="admin-filtres" onSubmit={delivrer}>
        <label className="admin-choix" htmlFor="cle-nom">Partenaire :</label>
        <input id="cle-nom" type="search" value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Le Soleil, rubrique économie" maxLength={80} />
        <button type="submit" className="primaire petit" disabled={nom.trim().length < 2}>Délivrer une clé</button>
      </form>

      {nouvelle && (
        <section className="admin-panneau admin-cle-nouvelle" aria-label="Nouvelle clé">
          <p><strong>Clé de « {nouvelle.nom} »</strong> : elle ne sera plus affichée.</p>
          <p><code className="admin-cle">{nouvelle.cle}</code></p>
          <button
            type="button"
            className="secondaire petit"
            onClick={() => navigator.clipboard.writeText(nouvelle.cle).then(() => setCopie(true)).catch(() => setCopie(false))}
          >
            <Copier />{copie ? "Clé copiée" : "Copier la clé"}
          </button>
        </section>
      )}
      {erreur && <p className="erreur-admin" role="alert">{erreur}</p>}

      <div className="tableau-defile admin-table" role="region" aria-label="Clés délivrées" tabIndex={0}>
        <table className="tableau">
          <thead>
            <tr>
              <th scope="col">Partenaire</th>
              <th scope="col">Délivrée</th>
              <th scope="col">Dernier appel</th>
              <th scope="col" className="nombre">Appels</th>
              <th scope="col">État</th>
              <th scope="col"><span className="sr-only">Action</span></th>
            </tr>
          </thead>
          <tbody>
            {cles?.length === 0 && (
              <tr><td colSpan={6}>Aucune clé délivrée.</td></tr>
            )}
            {cles?.map((c) => (
              <tr key={c.id}>
                <th scope="row">{c.nom}</th>
                <td className="admin-heure">{date.format(new Date(c.creee_le))} · {c.creee_par}</td>
                <td className="admin-heure">{c.vue_le ? date.format(new Date(c.vue_le)) : "jamais"}</td>
                <td className="nombre">{c.appels.toLocaleString("fr-FR")}</td>
                <td><span className={c.active ? "badge exacte" : "badge"}>{c.active ? "Active" : "Révoquée"}</span></td>
                <td>{c.active && <button type="button" className="lien-bouton" onClick={() => revoquer(c)}>Révoquer</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Cadre>
  );
}
