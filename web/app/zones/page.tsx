"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Entete, PiedDePage } from "@/components/Entete";
import { Fleche } from "@/components/icones";
import { OngletsDonnees } from "@/components/OngletsDonnees";
import { useLangue } from "@/i18n/langue";
import { REGIONS } from "@/lib/regions";
import { TUILES } from "@/lib/situer";
import { ZONES_FICHE } from "@/lib/zones";

/** « Ma région en chiffres » : choisir une région sur le schéma des 14 régions, ou comparer deux zones. */
export default function Zones() {
  const { t } = useLangue();
  const router = useRouter();
  const [a, setA] = useState("SN-DK");
  const [b, setB] = useState("SN-KD");

  return (
    <div className="site">
      <Entete actif="zones" />
      <main id="contenu" tabIndex={-1} className="zones-page">
        <OngletsDonnees actif="zones" />
        <h1 className="titre-situer">{t("zones.titre")}</h1>
        <p className="chapeau">{t("zones.intro")}</p>

        <section className="carte" aria-labelledby="titre-zones-carte">
          <h2 id="titre-zones-carte" className="sous-titre">{t("zones.choisir")}</h2>
          <nav className="carte-regions zones-carte" aria-labelledby="titre-zones-carte">
            {REGIONS.map((r) => {
              const pos = TUILES[r.code];
              return (
                <Link key={r.code} href={`/zones/${r.code}`} className="tuile zone-tuile" style={{ gridRow: pos.ligne, gridColumn: pos.colonne }}>
                  <span className="tuile-nom">{r.libelle}</span>
                </Link>
              );
            })}
          </nav>
          <p className="source-ligne visible discret">{t("situer.carte.schema")}</p>
          <Link href="/zones/SN" className="lien">{t("zones.senegal")} <Fleche taille={16} /></Link>
        </section>

        <section className="carte" aria-labelledby="titre-zones-comparer">
          <h2 id="titre-zones-comparer" className="sous-titre">{t("zones.comparerTitre")}</h2>
          <p className="aide">{t("zones.comparerAide")}</p>
          <form
            className="zones-comparer"
            onSubmit={(e) => {
              e.preventDefault();
              if (a !== b) router.push(`/zones/comparer?a=${a}&b=${b}`);
            }}
          >
            {([["zone-a", a, setA, "zones.zoneA"], ["zone-b", b, setB, "zones.zoneB"]] as const).map(([id, valeur, choisir, cle]) => (
              <div key={id} className="explorer-champ">
                <label htmlFor={id}>{t(cle)}</label>
                <select id={id} value={valeur} onChange={(e) => choisir(e.target.value)}>
                  {ZONES_FICHE.map((z) => <option key={z.code} value={z.code}>{z.libelle}</option>)}
                </select>
              </div>
            ))}
            <button type="submit" className="primaire" disabled={a === b}>{t("zones.comparer")}</button>
          </form>
          {a === b && <p className="note" role="status">{t("zones.memeZone")}</p>}
        </section>
      </main>
      <PiedDePage />
    </div>
  );
}
