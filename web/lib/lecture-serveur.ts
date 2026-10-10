import { cache } from "react";
import type { AskResponse } from "@contracts/ask_response";

// Lecture d'une réponse côté serveur (rendu de la page, aperçu de partage, image) : dans Docker, le serveur web
// joint l'API par le réseau interne.
const API = process.env.API_INTERNE ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** null si l'API ne répond pas vite ou ne connaît pas l'id : la page prend alors le relais côté navigateur. */
export const lireReponseServeur = cache(async (id: string): Promise<AskResponse | null> => {
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
