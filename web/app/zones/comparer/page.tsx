"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { Livre } from "@/components/icones";
import { OngletsDonnees } from "@/components/OngletsDonnees";
import { useLangue } from "@/i18n/langue";
import { profilZone, type ProfilZone, type ValeurCle } from "@/lib/api";
import { chiffres, titreSource } from "@/lib/typo";
import { libelleZone, parTheme, ZONES_FICHE } from "@/lib/zones";

export default function Page() {
  return (
    <Suspense>
      <Comparer />
    </Suspense>
  );
}

/**
 * Deux zones côte à côte sur les mêmes chiffres clés (« Dakar ou Kolda ? »). Chaque valeur est celle de la fiche
 * de la zone, avec sa période : aucune différence n'est calculée, et une période différente est signalée.
 * Les deux zones sont dans l'adresse : la comparaison se partage telle quelle.
 */
function Comparer() {
  const { t } = useLangue();
  const router = useRouter();
  const params = useSearchParams();
  const a = params.get("a") ?? "SN-DK";
  const b = params.get("b") ?? "SN-KD";
  const [profils, setProfils] = useState<[ProfilZone, ProfilZone] | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [essai, setEssai] = useState(0);

  useEffect(() => {
    let annule = false;
    setProfils(null);
    setErreur(null);
    Promise.all([profilZone(a), profilZone(b)])
      .then((r) => !annule && setProfils(r))
      .catch((e) => !annule && setErreur(e));
    return () => {
      annule = true;
    };
  }, [a, b, essai]);

  const titre = t("comparer.titre", { a: libelleZone(a), b: libelleZone(b) });
  useEffect(() => {
    document.title = `${titre} · Gëstukaay`;
  }, [titre]);

  function changer(cle: "a" | "b", code: string) {
    const p = new URLSearchParams({ a, b, [cle]: code });
    router.replace(`/zones/comparer?${p}`, { scroll: false });
  }

  const [pa, pb] = profils ?? [null, null];
  const deB = (c: ValeurCle) => pb?.chiffres.find((x) => x.indicateur.code === c.indicateur.code);
  // Les indicateurs que seule la zone B publie viennent aussi, à la fin de leur thème
  const lignes = pa && pb ? [...pa.chiffres, ...pb.chiffres.filter((c) => !pa.chiffres.some((x) => x.indicateur.code === c.indicateur.code))] : [];
  const sources = profils ? [...new Map(profils.flatMap((p) => p.chiffres).map((c) => [c.source.url, c.source])).values()] : [];

  const cellule = (c: ValeurCle | undefined) =>
    c ? (
      <td className="nombre">
        <strong>{chiffres(c.valeur_affichee)}</strong>
        <small>{c.libelle_periode}{c.nature === "projection" ? ` · ${t("reponse.projection")}` : c.nature === "estimation" ? ` · ${t("reponse.estimation")}` : ""}</small>
      </td>
    ) : (
      <td className="nombre absent">{t("comparer.nonPublie")}</td>
    );

  return (
    <div className="site">
      <Entete actif="zones" />
      <main id="contenu" tabIndex={-1} className="zones-page">
        <OngletsDonnees actif="zones" />
        <nav aria-label={t("zone.ariane")} className="ariane">
          <Link href="/zones">{t("zones.titre")}</Link>
          <span aria-hidden="true">/</span>
          <span>{t("zones.comparerTitre")}</span>
        </nav>
        <h1 className="titre-situer">{titre}</h1>

        <form className="zones-comparer" aria-label={t("zones.comparerTitre")} onSubmit={(e) => e.preventDefault()}>
          {(["a", "b"] as const).map((cle) => (
            <div key={cle} className="explorer-champ">
              <label htmlFor={`comparer-${cle}`}>{t(cle === "a" ? "zones.zoneA" : "zones.zoneB")}</label>
              <select id={`comparer-${cle}`} value={cle === "a" ? a : b} onChange={(e) => changer(cle, e.target.value)}>
                {ZONES_FICHE.filter((z) => z.code !== (cle === "a" ? b : a)).map((z) => (
                  <option key={z.code} value={z.code}>{z.libelle}</option>
                ))}
              </select>
            </div>
          ))}
        </form>

        {erreur ? (
          <Erreur erreur={erreur} onReessayer={() => setEssai((n) => n + 1)} />
        ) : !pa || !pb ? (
          <Chargement />
        ) : (
          <section className="carte comparer-carte">
            <div className="tableau-defile" role="region" aria-label={titre} tabIndex={0}>
              <table className="tableau comparer-tableau">
                <thead>
                  <tr>
                    <th scope="col">{t("comparer.indicateur")}</th>
                    <th scope="col" className="nombre"><Link href={`/zones/${a}`}>{pa.zone.libelle}</Link></th>
                    <th scope="col" className="nombre"><Link href={`/zones/${b}`}>{pb.zone.libelle}</Link></th>
                  </tr>
                </thead>
                {parTheme(lignes).map(([theme, liste]) => (
                  <tbody key={theme}>
                    <tr className="comparer-theme"><th scope="colgroup" colSpan={3}>{theme}</th></tr>
                    {liste.map((c) => {
                      const ca = pa.chiffres.find((x) => x.indicateur.code === c.indicateur.code);
                      const cb = deB(c);
                      return (
                        <tr key={c.indicateur.code}>
                          <th scope="row">
                            {c.indicateur.libelle}
                            <small>{c.unite}{ca && cb && ca.periode !== cb.periode ? ` · ${t("comparer.periodes")}` : ""}</small>
                          </th>
                          {cellule(ca)}
                          {cellule(cb)}
                        </tr>
                      );
                    })}
                  </tbody>
                ))}
              </table>
            </div>
            <p className="note">{t("comparer.note")}</p>
            <aside className="bloc-source" aria-label={t("explorer.sources")}>
              <p className="bloc-source-titre"><Livre />{t("explorer.sources")}</p>
              {sources.map((src) => (
                <div key={src.url}>
                  <p>{titreSource(src.titre)}</p>
                  <p className="discret">{src.libelle}</p>
                </div>
              ))}
            </aside>
          </section>
        )}
      </main>
      <PiedDePage />
    </div>
  );
}
