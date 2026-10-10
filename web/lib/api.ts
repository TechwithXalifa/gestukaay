import type { AskRequest } from "@contracts/ask_request";
import type { AskResponse } from "@contracts/ask_response";
import type { CatalogueResponse } from "@contracts/catalogue_response";
import type { FicheIndicateur } from "@contracts/fiche_indicateur";
import type { FeedbackRequest } from "@contracts/feedback_request";
import type { Problem } from "@contracts/problem";
import type { SeriesResponse } from "@contracts/series_response";
import type { SituateRequest } from "@contracts/situate_request";
import type { SituateResponse } from "@contracts/situate_response";
import type { TranscriptionResponse } from "@contracts/transcription_response";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE = API_URL;

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
  // Lectures sans en-tête : une requête simple, sans requête CORS préalable (un aller-retour de moins en 3G,
  // audit du 09/10). Envois : JSON, et l'identifiant d'onglet qui sert à la limite de requêtes (securite.py)
  const envoi = (init?.method ?? "GET") !== "GET";
  try {
    r = await fetch(`${BASE}${chemin}`, {
      ...init,
      headers: envoi ? { "Content-Type": "application/json", ...enteteClient(), ...init?.headers } : init?.headers,
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

const CLE_CONVERSATION = "gestukaay.conversation";

/**
 * Identifiant de conversation, un par onglet (décision 0021) : il permet « et pour Kaolack ? » sur
 * 3 échanges. Tiré au hasard, ne dit rien de la personne, oublié à la fermeture de l'onglet ; le
 * backend le hache avant de le journaliser. Sans stockage disponible, chaque question est isolée.
 */
export function conversationId(): string | undefined {
  try {
    let id = sessionStorage.getItem(CLE_CONVERSATION);
    if (!id) {
      id = typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
      sessionStorage.setItem(CLE_CONVERSATION, id);
    }
    return id;
  } catch {
    return undefined;
  }
}

/** Identifiant d'onglet pour la limite de requêtes : une salle sur le même Wi-Fi ne partage plus un quota. */
function enteteClient(): Record<string, string> {
  const id = conversationId();
  return id ? { "X-Gestukaay-Client": id } : {};
}

export const demander = (req: AskRequest) =>
  requete<AskResponse>("/v1/ask", {
    method: "POST",
    body: JSON.stringify({ conversation_id: conversationId(), ...req }),
  });

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
    r = await fetch(`${BASE}/v1/transcrire`, { method: "POST", body: corps, headers: enteteClient() });
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

// ---- v1.4.0 : catalogue, fiche indicateur et séries d'Explorer (décision 0023) ----

function parametres(p: Record<string, string | number | undefined | null>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  return q.toString();
}

export type FiltreCatalogue = { domaine?: string; q?: string; niveau?: string; limite?: number; decalage?: number };

export const catalogue = (f: FiltreCatalogue = {}) =>
  requete<CatalogueResponse>(`/v1/indicators?${parametres(f)}`);

export const fiche = (code: string) => requete<FicheIndicateur>(`/v1/indicators/${encodeURIComponent(code)}`);

/** Autocomplétion de la question (EF-10) : route de confort du site, hors contrat public (suggestions.py). */
export type Suggestion = { texte: string; indicateur: { code: string; libelle: string } | null };

export const suggerer = (q: string, signal?: AbortSignal) =>
  requete<{ suggestions: Suggestion[] }>(`/v1/suggestions?${parametres({ q })}`, { signal });

export type DemandeSeries = { indicateur: string; zones: string[]; debut?: string; fin?: string };

const parametresSeries = (d: DemandeSeries) =>
  parametres({ indicateur: d.indicateur, zones: d.zones.join(","), debut: d.debut, fin: d.fin });

export const series = (d: DemandeSeries) => requete<SeriesResponse>(`/v1/series?${parametresSeries(d)}`);

/** Carte des 14 régions (Explorer, vue « Carte ») : route du site, hors contrat public (carte.py). */
export type ValeurCarte = {
  region: string;
  zone: { code: string; libelle: string; niveau: string };
  valeur: number;
  valeur_affichee: string;
  nature: string | null;
};
export type CarteResponse = {
  version_socle: string;
  indicateur: { code: string; libelle: string };
  unite: string;
  periode: string | null;
  libelle_periode: string | null;
  periodes: string[];
  valeurs: ValeurCarte[];
  absents: string[];
  ensemble: ValeurCarte | null;
  sources: SeriesResponse["series"][number]["source"][];
};

export const carte = (indicateur: string, periode?: string) =>
  requete<CarteResponse>(`/v1/carte?${parametres({ indicateur, periode })}`);

/** « Ma région en chiffres » : chiffres clés d'une zone (route du site, hors contrat public : profil_zone.py). */
export type ValeurCle = {
  theme: string;
  indicateur: { code: string; libelle: string };
  unite: string;
  zone_servie: { code: string; libelle: string; niveau: string };
  periode: string;
  libelle_periode: string;
  valeur: number;
  valeur_affichee: string;
  nature: string | null;
  rang: number | null;
  sur: number | null;
  source: SeriesResponse["series"][number]["source"];
};
export type ProfilZone = {
  version_socle: string;
  zone: { code: string; libelle: string; niveau: string };
  chiffres: ValeurCle[];
  absents: { code: string; libelle: string }[];
};

export const profilZone = (code: string) => requete<ProfilZone>(`/v1/zones/${encodeURIComponent(code)}`);

/** Export CSV de la vue Explorer (EF-34), virgule décimale pour Excel en français. */
export const seriesCsvUrl = (d: DemandeSeries) => `${BASE}/v1/series.csv?${parametresSeries(d)}&decimale=virgule`;
