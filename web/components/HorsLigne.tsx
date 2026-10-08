"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { Cle } from "@/i18n/fr";
import { useLangue } from "@/i18n/langue";
import { type Consultation, historique } from "@/lib/historique";
import { chiffres } from "@/lib/typo";
import { Wifi } from "./icones";

function quand(iso: string, t: (c: Cle, v?: Record<string, string>) => string): string {
  const d = new Date(iso);
  const jours = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (jours === 0) return t("horsligne.aHeure", { heure: d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) });
  return jours === 1 ? t("horsligne.hier") : t("horsligne.le", { date: d.toLocaleDateString("fr-FR") });
}

/** État « Hors ligne » (7.3, maquette M-HorsLigne) : les dernières réponses restent lisibles. */
export function HorsLigne({ onReessayer }: { onReessayer: () => void }) {
  const { t } = useLangue();
  const [liste, setListe] = useState<Consultation[]>([]);
  useEffect(() => setListe(historique()), []);
  const exactes = liste.filter((c) => c.reponse.reponse.issue === "exacte");

  return (
    <div className="hors-ligne">
      <section role="status" className="bandeau">
        <div className="bandeau-texte">
          <Wifi />
          <div>
            <h1>{t("horsligne.titre")}</h1>
            <p>{t("horsligne.texte")}</p>
          </div>
        </div>
        <button type="button" className="primaire-sombre" onClick={onReessayer}>{t("etat.reessayer")}</button>
      </section>

      {exactes.length > 0 && (
        <>
          <h2 className="eyebrow-gris">{t("horsligne.recentes")}</h2>
          <ul className="recentes">
            {exactes.map(({ reponse, consulteeLe }) => {
              const r = reponse.reponse;
              if (r.issue !== "exacte") return null;
              const v = r.resultats[0];
              return (
                <li key={r.id}>
                  <Link href={`/r/${r.id}`}>
                    <span className="discret">{v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}</span>
                    <span className="valeur-petite">{chiffres(v.valeur_affichee)} <span>{v.unite}</span></span>
                    <span className="discret">{v.source.libelle} · {quand(consulteeLe, t)}</span>
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
