import type { AskRequest } from "@contracts/ask_request";
import type { AskResponse } from "@contracts/ask_response";
import type { Problem } from "@contracts/problem";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function appeler(chemin: string, corps: unknown): Promise<AskResponse> {
  const r = await fetch(`${BASE}${chemin}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corps),
  });
  if (!r.ok) {
    const p = (await r.json().catch(() => null)) as Problem | null;
    throw new Error(p?.title ?? `Erreur ${r.status}`);
  }
  return r.json();
}

export const demander = (req: AskRequest) => appeler("/v1/ask", req);

export const confirmer = (id: string, choixId: string) =>
  appeler(`/v1/ask/${id}/confirm`, { choix_id: choixId });
