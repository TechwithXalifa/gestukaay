import type { SeriesResponse } from "@contracts/series_response";

// Lecture côté serveur du widget : dans Docker, le serveur web joint l'API par le réseau interne.
const API = process.env.API_INTERNE ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type DerniereValeur = {
  indicateur: string;
  zone: string;
  valeur: string;
  unite: string;
  periode: string;
  nature: string | null;
  source: string;
  publication: string;
};

/**
 * Dernière valeur publiée d'un indicateur pour une zone, comme la fiche indicateur : jamais une projection
 * au-delà de l'année en cours (décision 0035). Relue au plus toutes les heures : le widget suit les nouvelles
 * versions du socle sans recharger l'API à chaque affichage. null si l'indicateur ou la zone ne publie rien.
 */
export async function derniereValeur(code: string, zone: string): Promise<DerniereValeur | null> {
  try {
    const p = new URLSearchParams({ indicateur: code, zones: zone });
    const r = await fetch(`${API}/v1/series?${p}`, { next: { revalidate: 3600 }, signal: AbortSignal.timeout(3000) });
    if (!r.ok) return null;
    const s = (await r.json()) as SeriesResponse;
    const serie = s.series[0];
    const points = serie?.points ?? [];
    const an = new Date().getFullYear();
    const passes = points.filter((x) => Number(x.periode.slice(0, 4)) <= an);
    const point = (passes.length ? passes : points).at(-1);
    if (!serie || !point) return null;
    return {
      indicateur: s.indicateur.libelle, zone: serie.zone.libelle, valeur: point.valeur_affichee, unite: s.unite,
      periode: point.libelle, nature: point.nature ?? null, source: serie.source.libelle, publication: serie.source.url,
    };
  } catch {
    return null;
  }
}
