import type { Metadata } from "next";
import { headers } from "next/headers";
import { PageReponse } from "@/components/PageReponse";
import { lireReponseServeur } from "@/lib/lecture-serveur";

// Rendu serveur de la page réponse (cahier 7.6) : le chiffre arrive dans le HTML, sans attendre
// le JavaScript puis l'API. Dans Docker, le serveur web joint l'API par le réseau interne.

type Params = { params: Promise<{ id: string }> };

/** Adresse publique du site, lue sur la requête (derrière Caddy : Host et X-Forwarded-Proto) : l'image de
 *  l'aperçu doit avoir une adresse absolue pour WhatsApp. */
async function adresseDuSite(): Promise<URL | undefined> {
  const h = await headers();
  const hote = h.get("x-forwarded-host") ?? h.get("host");
  if (!hote) return undefined;
  const protocole = h.get("x-forwarded-proto") ?? (hote.startsWith("localhost") ? "http" : "https");
  return new URL(`${protocole}://${hote}`);
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const rep = await lireReponseServeur((await params).id);
  if (!rep) return {};
  const r = rep.reponse;
  // Aperçu de partage (WhatsApp, Telegram, réseaux) : la question en titre, le chiffre et sa source en description
  const v = r.issue === "exacte" ? r.resultats.find((x) => x.mise_en_evidence) ?? r.resultats[0] : null;
  const description = v
    ? `${v.valeur_affichee}${v.unite ? ` ${v.unite}` : ""} · ${v.indicateur.libelle} · ${v.zone.libelle} · ${v.periode.libelle}. Source : ${v.source.libelle}`
    : "Le chiffre officiel du Sénégal, avec sa source et sa date.";
  return {
    title: r.question,
    description,
    metadataBase: await adresseDuSite(),
    openGraph: { title: r.question, description, type: "article", siteName: "Gëstukaay", locale: "fr_SN" },
    twitter: { card: "summary_large_image", title: r.question, description },
  };
}

export default async function Page({ params }: Params) {
  const { id } = await params;
  return <PageReponse id={id} initiale={await lireReponseServeur(id)} />;
}
