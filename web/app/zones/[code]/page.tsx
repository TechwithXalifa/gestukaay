"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ChiffreCle } from "@/components/ChiffreCle";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { OngletsDonnees } from "@/components/OngletsDonnees";
import { useLangue } from "@/i18n/langue";
import { ErreurApi, profilZone, type ProfilZone } from "@/lib/api";
import { parTheme, ZONES_FICHE } from "@/lib/zones";

/**
 * « Ma région en chiffres » : les chiffres clés d'une zone, rangés par thème, chacun avec sa dernière valeur
 * publiée, sa source et, pour une région, son rang parmi les 14. Répond aux « parle-moi de Matam ».
 */
export default function FicheZone() {
  const { t } = useLangue();
  const router = useRouter();
  const { code } = useParams<{ code: string }>();
  const zone = decodeURIComponent(code);
  const [p, setP] = useState<ProfilZone | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [essai, setEssai] = useState(0);

  useEffect(() => {
    let annule = false;
    setP(null);
    setErreur(null);
    profilZone(zone).then((r) => !annule && setP(r)).catch((e) => !annule && setErreur(e));
    return () => {
      annule = true;
    };
  }, [zone, essai]);

  useEffect(() => {
    if (p) document.title = `${t("zone.titre", { zone: p.zone.libelle })} · Gëstukaay`;
  }, [p, t]);

  const introuvable = erreur instanceof ErreurApi && erreur.statut === 404;

  return (
    <div className="site">
      <Entete actif="zones" />
      <main id="contenu" tabIndex={-1} className="zones-page">
        <OngletsDonnees actif="zones" />
        <nav aria-label={t("zone.ariane")} className="ariane">
          <Link href="/zones">{t("zones.titre")}</Link>
          <span aria-hidden="true">/</span>
          <span>{p?.zone.libelle ?? "…"}</span>
        </nav>

        {introuvable ? (
          <section className="carte">
            <h1 className="titre-etat">{t("zone.introuvable")}</h1>
            <Link href="/zones" className="lien">{t("zones.titre")}</Link>
          </section>
        ) : erreur ? (
          <Erreur erreur={erreur} onReessayer={() => setEssai((n) => n + 1)} />
        ) : !p ? (
          <Chargement />
        ) : (
          <>
            <h1 className="titre-situer">{t("zone.titre", { zone: p.zone.libelle })}</h1>
            <p className="chapeau">{t(p.zone.niveau === "region" ? "zone.introRegion" : "zone.introPays")}</p>

            <div className="explorer-champ zone-comparer">
              <label htmlFor="zone-comparer">{t("zone.comparer")}</label>
              <select
                id="zone-comparer"
                value=""
                onChange={(e) => e.target.value && router.push(`/zones/comparer?a=${p.zone.code}&b=${e.target.value}`)}
              >
                <option value="">{t("zone.choisir")}</option>
                {ZONES_FICHE.filter((z) => z.code !== p.zone.code).map((z) => (
                  <option key={z.code} value={z.code}>{z.libelle}</option>
                ))}
              </select>
            </div>

            {parTheme(p.chiffres).map(([theme, liste]) => (
              <section key={theme} className="zone-theme" aria-labelledby={`theme-${theme}`}>
                <h2 id={`theme-${theme}`} className="sous-titre">{theme}</h2>
                <ul className="chiffres-cles">
                  {liste.map((c) => <ChiffreCle key={c.indicateur.code} c={c} zone={p.zone.code} />)}
                </ul>
              </section>
            ))}

            {p.absents.length > 0 && (
              <p className="note">{t("zone.absents", { liste: p.absents.map((a) => a.libelle).join(", ") })}</p>
            )}
            <p className="note">{t("zone.methode", { version: p.version_socle })}</p>
          </>
        )}
      </main>
      <PiedDePage />
    </div>
  );
}
