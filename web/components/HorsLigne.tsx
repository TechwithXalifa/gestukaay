"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { type Consultation, historique } from "@/lib/historique";
import { Wifi } from "./icones";

function quand(iso: string): string {
  const d = new Date(iso);
  const jours = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (jours === 0) return `consultée à ${d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`;
  return jours === 1 ? "consultée hier" : `consultée le ${d.toLocaleDateString("fr-FR")}`;
}

/** État « Hors ligne » (7.3, maquette M-HorsLigne) : les dernières réponses restent lisibles. */
export function HorsLigne({ onReessayer }: { onReessayer: () => void }) {
  const [liste, setListe] = useState<Consultation[]>([]);
  useEffect(() => setListe(historique()), []);
  const exactes = liste.filter((c) => c.reponse.reponse.issue === "exacte");

  return (
    <div className="hors-ligne">
      <section role="status" className="bandeau">
        <div className="bandeau-texte">
          <Wifi />
          <div>
            <h1>Vous êtes hors ligne.</h1>
            <p>Vos dernières réponses restent lisibles. Les nouvelles questions demandent une connexion.</p>
          </div>
        </div>
        <button type="button" className="primaire-sombre" onClick={onReessayer}>Réessayer</button>
      </section>

      {exactes.length > 0 && (
        <>
          <h2 className="eyebrow-gris">Consultées récemment · disponibles sans connexion</h2>
          <ul className="recentes">
            {exactes.map(({ reponse, consulteeLe }) => {
              const r = reponse.reponse;
              if (r.issue !== "exacte") return null;
              const v = r.resultats[0];
              return (
                <li key={r.id}>
                  <Link href={`/r/${r.id}`}>
                    <span className="discret">{v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}</span>
                    <span className="valeur-petite">{v.valeur_affichee} <span>{v.unite}</span></span>
                    <span className="discret">{v.source.libelle} · {quand(consulteeLe)}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
