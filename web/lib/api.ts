import type { AskRequest } from "@contracts/ask_request";
import type { AskResponse } from "@contracts/ask_response";
import type { FeedbackRequest } from "@contracts/feedback_request";
import type { Problem } from "@contracts/problem";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Erreur affichable : jamais de trace technique, un code d'incident discret (7.3). */
export class ErreurApi extends Error {
  constructor(
    message: string,
    readonly statut: number,
    readonly horsLigne = false,
    readonly codeIncident: string | null = null,
  ) {
    super(message);
  }
}

async function requete<T>(chemin: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`${BASE}${chemin}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    const horsLigne = typeof navigator !== "undefined" && !navigator.onLine;
    throw new ErreurApi("Le service ne répond pas.", 0, horsLigne);
  }
  if (!r.ok) {
    const p = (await r.json().catch(() => null)) as Problem | null;
    throw new ErreurApi(p?.title ?? "Le service ne répond pas.", r.status, false, p?.code_incident ?? null);
  }
  return (r.status === 204 ? undefined : await r.json()) as T;
}

export const demander = (req: AskRequest) =>
  requete<AskResponse>("/v1/ask", { method: "POST", body: JSON.stringify(req) });

export const confirmer = (id: string, choixId: string) =>
  requete<AskResponse>(`/v1/ask/${id}/confirm`, {
    method: "POST",
    body: JSON.stringify({ choix_id: choixId }),
  });

export const lireReponse = (id: string) => requete<AskResponse>(`/v1/answers/${id}`);

export const envoyerRetour = (retour: FeedbackRequest) =>
  requete<void>("/v1/feedback", { method: "POST", body: JSON.stringify(retour) });
