"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CANAUX, Cadre, Choix, Connexion, useAdmin } from "@/components/Admin";

/**
 * Questions non résolues regroupées par thème (back-office, route /admin/non-resolues). Les refus d'une période,
 * regroupés par leurs mots utiles (zones, années, mots outils retirés), le thème le plus fréquent d'abord. Pour
 * chaque thème, les indicateurs du catalogue qui en contiennent les mots : s'il y en a, le chiffre existe et la
 * question a été mal comprise (lexique) ; sinon, il manque au socle.
 */
type Groupe = {
  theme: string;
  occurrences: number;
  langues: Record<string, number>;
  motifs: Record<string, number>;
  exemples: { question: string; reponse_id: string; recu_le: string }[];
  derniere: string;
  indicateurs_proches?: { code: string; libelle: string }[];
};

const PERIODES = [7, 30, 90] as const;
const MOTIFS: Record<string, string> = {
  hors_socle: "Hors socle",
  projection: "Projection",
  incomprehension: "Incompréhension",
  non_disponible: "Pas encore disponible",
  inconnu: "Sans motif",
};
const ISSUES = { aucune: "Refus", approchee: "Réponses approchées" };
const LANGUES = { fr: "Français", wo: "Wolof" };
const jour = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export default function NonResolues() {
  const { identifiant, role, avis, connecter, fermer, appeler } = useAdmin();
  const [jours, setJours] = useState<(typeof PERIODES)[number]>(30);
  const [filtres, setFiltres] = useState({ canal: "", langue: "", issue: "aucune" });
  const [donnees, setDonnees] = useState<{ questions: number; groupes: Groupe[] } | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (!identifiant) return;
    let annule = false;
    const p = new URLSearchParams({ jours: String(jours) });
    for (const [k, v] of Object.entries(filtres)) if (v) p.set(k, v);
    appeler(`/admin/non-resolues?${p}`)
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
  }, [identifiant, jours, filtres, appeler]);

  if (!identifiant) {
    return (
      <Cadre actif="non-resolues">
        <Connexion erreur={avis ?? erreur} verification={identifiant === undefined} onConnecter={connecter} />
      </Cadre>
    );
  }

  return (
    <Cadre actif="non-resolues" identifiant={identifiant} role={role} onFermer={() => { fermer(); setDonnees(null); }}>
      <div className="admin-titre">
        <h1 className="titre-etat">Questions non résolues, par thème</h1>
        <div role="group" aria-label="Période" className="bascule admin-periode">
          {PERIODES.map((j) => (
            <button key={j} type="button" aria-pressed={jours === j} onClick={() => setJours(j)}>{j} j</button>
          ))}
        </div>
      </div>
      <div className="admin-filtres">
        <Choix libelle="Issue" valeur={filtres.issue} onChange={(v) => setFiltres({ ...filtres, issue: v || "aucune" })} options={ISSUES} tous="Refus" />
        <Choix libelle="Canal" valeur={filtres.canal} onChange={(v) => setFiltres({ ...filtres, canal: v })} options={CANAUX} tous="Tous" />
        <Choix libelle="Langue" valeur={filtres.langue} onChange={(v) => setFiltres({ ...filtres, langue: v })} options={LANGUES} tous="Toutes" />
      </div>
      {erreur && <p className="erreur-admin" role="alert">{erreur}</p>}
      {donnees && (
        <p className="note" role="status">
          {donnees.questions} questions, {donnees.groupes.length} thèmes. Zones, années et mots outils sont retirés avant de regrouper.
        </p>
      )}
      {donnees?.groupes.length === 0 && <p className="note">Rien à regrouper sur la période.</p>}
      <ul className="admin-groupes">
        {donnees?.groupes.map((g) => (
          <li key={g.theme + g.derniere} className="admin-panneau">
            <div className="admin-groupe-tete">
              <h2 className="sous-titre">{g.theme}</h2>
              <strong className="admin-groupe-nombre">{g.occurrences}</strong>
            </div>
            <p className="note">
              {Object.entries(g.motifs).map(([m, n]) => `${MOTIFS[m] ?? m} : ${n}`).join(" · ")}
              {" · "}{Object.entries(g.langues).map(([l, n]) => `${l.toUpperCase()} ${n}`).join(", ")}
              {" · dernière le "}{jour.format(new Date(g.derniere))}
            </p>
            <ul className="admin-groupe-exemples">
              {g.exemples.map((e) => <li key={e.reponse_id}>« {e.question} »</li>)}
            </ul>
            {g.indicateurs_proches && g.indicateurs_proches.length > 0 ? (
              <div className="admin-groupe-pistes">
                <p className="note"><strong>Dans le catalogue</strong> : la question a sans doute été mal comprise (lexique).</p>
                <ul>
                  {g.indicateurs_proches.map((i) => (
                    <li key={i.code}><Link href={`/indicateurs/${encodeURIComponent(i.code)}`} target="_blank">{i.libelle}</Link></li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="note"><strong>Rien dans le catalogue</strong> : l&apos;indicateur manque sans doute au socle.</p>
            )}
          </li>
        ))}
      </ul>
    </Cadre>
  );
}
