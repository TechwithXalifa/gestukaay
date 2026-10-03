"use client";

import Link from "next/link";
import { Entete, PiedDePage } from "@/components/Entete";
import { useLangue } from "@/i18n/langue";
import { TOUS_LES_DOMAINES } from "@/lib/domaines";

/** Les 32 domaines du socle (décision 0005). Le catalogue des indicateurs viendra ensuite. */
export default function Domaines() {
  const { t } = useLangue();
  return (
    <div className="site">
      <Entete />
      <main id="contenu" tabIndex={-1} className="domaines-page">
        <p className="eyebrow">{t("domaines.eyebrow")}</p>
        <h1 className="titre-situer">{t("domaines.titre", { n: String(TOUS_LES_DOMAINES.length) })}</h1>
        <p className="explication">{t("domaines.intro")}</p>
        <ul className="liste-domaines">
          {TOUS_LES_DOMAINES.map((d) => (
            <li key={d}>{d}</li>
          ))}
        </ul>
        <Link href="/" className="primaire">{t("situer.question")}</Link>
      </main>
      <PiedDePage />
    </div>
  );
}
