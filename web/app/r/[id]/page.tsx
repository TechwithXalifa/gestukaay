import type { Metadata } from "next";
import { cache } from "react";
import type { AskResponse } from "@contracts/ask_response";
import { PageReponse } from "@/components/PageReponse";

// Rendu serveur de la page réponse (cahier 7.6) : le chiffre arrive dans le HTML, sans attendre
// le JavaScript puis l'API. Dans Docker, le serveur web joint l'API par le réseau interne.
const API = process.env.API_INTERNE ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** null si l'API ne répond pas vite ou ne connaît pas l'id : la page prend alors le relais. */
const lire = cache(async (id: string): Promise<AskResponse | null> => {
  try {
    const r = await fetch(`${API}/v1/answers/${encodeURIComponent(id)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1500),
    });
    return r.ok ? ((await r.json()) as AskResponse) : null;
  } catch {
    return null;
  }
});

type Params = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const rep = await lire((await params).id);
  return rep ? { title: rep.reponse.question } : {};
}

export default async function Page({ params }: Params) {
  const { id } = await params;
  return <PageReponse id={id} initiale={await lire(id)} />;
}
