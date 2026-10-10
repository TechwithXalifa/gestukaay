import type { Metadata } from "next";
import { chiffres } from "@/lib/typo";
import { derniereValeur } from "@/lib/widget";

// Widget à intégrer : un chiffre officiel toujours à jour, qu'un média, une mairie ou une école colle sur son site
// (<iframe>). Page minimale, sans en-tête ni pied, rendue côté serveur ; seule adresse du site autorisée en cadre
// (next.config.mjs). Le lien ouvre Gëstukaay dans un nouvel onglet, avec l'évolution et la source.

type Props = { params: Promise<{ code: string }>; searchParams: Promise<{ zone?: string; theme?: string }> };

export const metadata: Metadata = { title: "Widget", robots: { index: false } };

export default async function Widget({ params, searchParams }: Props) {
  const code = decodeURIComponent((await params).code);
  const { zone = "SN", theme } = await searchParams;
  const v = await derniereValeur(code, zone);
  const sombre = theme === "sombre";
  const explorer = `/explorer?indicateur=${encodeURIComponent(code)}&zones=${encodeURIComponent(zone === "SN" ? "SN" : `SN,${zone}`)}`;
  return (
    <main className={sombre ? "widget sombre" : "widget"} lang="fr">
      {v ? (
        <>
          <p className="widget-titre">{v.indicateur} · {v.zone}</p>
          <p className="widget-valeur">
            <span>{chiffres(v.valeur)}</span> {v.unite && <span className="widget-unite">{v.unite}</span>}
          </p>
          <p className="widget-source">
            {v.periode}
            {v.nature === "projection" ? " · projection officielle" : v.nature === "estimation" ? " · estimation officielle" : ""}
            {" · "}{v.source}
          </p>
          <a className="widget-lien" href={explorer} target="_blank" rel="noopener">Gëstukaay · le chiffre officiel, avec sa source</a>
        </>
      ) : (
        <>
          <p className="widget-titre">Chiffre indisponible</p>
          <p className="widget-source">Cet indicateur n'est pas publié pour cette zone, ou le service ne répond pas.</p>
          <a className="widget-lien" href="/" target="_blank" rel="noopener">Gëstukaay · le chiffre officiel, avec sa source</a>
        </>
      )}
    </main>
  );
}
