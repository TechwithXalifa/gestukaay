"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Entete, PiedDePage } from "@/components/Entete";
import { OngletsDonnees } from "@/components/OngletsDonnees";
import { useLangue } from "@/i18n/langue";
import { catalogue } from "@/lib/api";
import { TOUS_LES_DOMAINES } from "@/lib/domaines";
import { nombre } from "@/lib/typo";

/**
 * Les 32 domaines du socle (décision 0005). Chaque domaine ouvre le catalogue filtré sur lui ; le nombre
 * d'indicateurs vient de l'API au chargement, il suit donc le socle servi. Sans réponse (hors ligne,
 * moteur indisponible), les liens restent, sans nombre.
 */
export default function Domaines() {
  const { t } = useLangue();
  const [nombres, setNombres] = useState<Record<string, number>>({});

  useEffect(() => {
    let actif = true;
    Promise.allSettled(TOUS_LES_DOMAINES.map((d) => catalogue({ domaine: d, limite: 1 }).then((r) => [d, r.total] as const)))
      .then((res) => {
        if (!actif) return;
        setNombres(Object.fromEntries(res.flatMap((r) => (r.status === "fulfilled" ? [r.value] : []))));
      });
    return () => {
      actif = false;
    };
  }, []);

  return (
    <div className="site">
      <Entete actif="donnees" />
      <main id="contenu" tabIndex={-1} className="domaines-page">
        <OngletsDonnees actif="domaines" />
        <h1 className="titre-situer">{t("domaines.titre", { n: String(TOUS_LES_DOMAINES.length) })}</h1>
        <p className="explication">{t("domaines.intro")}</p>
        <ul className="liste-domaines">
          {TOUS_LES_DOMAINES.map((d) => {
            const n = nombres[d];
            return (
              <li key={d}>
                <Link
                  href={`/indicateurs?domaine=${encodeURIComponent(d)}`}
                  aria-label={!n ? d : n === 1 ? t("domaines.lienUn", { domaine: d }) : t("domaines.lien", { domaine: d, n: nombre(n) })}
                >
                  {d}
                  {n ? <span className="liste-domaines-nombre" aria-hidden="true">{nombre(n)}</span> : null}
                </Link>
              </li>
            );
          })}
        </ul>
        <Link href="/" className="primaire">{t("situer.question")}</Link>
      </main>
      <PiedDePage />
    </div>
  );
}
