import type { AskRequest } from "@contracts/ask_request";
import type { AskResponse } from "@contracts/ask_response";
import type { FeedbackRequest } from "@contracts/feedback_request";
import type { Problem } from "@contracts/problem";
import type { SituateRequest } from "@contracts/situate_request";
import type { SituateResponse } from "@contracts/situate_response";
import type { TranscriptionResponse } from "@contracts/transcription_response";

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

/** « Où je me situe » (décision 0004 §2) : rien n'est conservé, ni ici ni côté serveur. */
export const situer = (req: SituateRequest) =>
  requete<SituateResponse>("/v1/situate", { method: "POST", body: JSON.stringify(req) });

export const lireReponse =(id: string) => requete<AskResponse>(`/v1/answers/${id}`);

export const envoyerRetour = (retour: FeedbackRequest) =>
  requete<void>("/v1/feedback", { method: "POST", body: JSON.stringify(retour) });

/** Voix sur le web (décision 0004 §1) : audio -> texte à corriger avant /v1/ask. */
export async function transcrire(audio: Blob, langue: "fr" | "wo" | "auto" = "auto"): Promise<TranscriptionResponse> {
  const corps = new FormData();
  corps.append("fichier", audio, audio.type.includes("ogg") ? "question.ogg" : "question.webm");
  corps.append("langue", langue);
  let r: Response;
  try {
    r = await fetch(`${BASE}/v1/transcrire`, { method: "POST", body: corps });
  } catch {
    throw new ErreurApi("Le service ne répond pas.", 0, typeof navigator !== "undefined" && !navigator.onLine);
  }
  if (!r.ok) {
    const p = (await r.json().catch(() => null)) as Problem | null;
    throw new ErreurApi(p?.title ?? "Le service ne répond pas.", r.status, false, p?.code_incident ?? null);
  }
  return r.json();
}

/** Exports d'une réponse exacte (EF-33, EF-34) : liens de téléchargement directs. */
export const exportUrl = (id: string, format: "pdf" | "csv") => `${BASE}/v1/answers/${id}/export.${format}`;
