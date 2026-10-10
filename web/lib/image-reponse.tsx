import { ImageResponse } from "next/og";
import type { AskResponse, ReponseExacte } from "@contracts/ask_response";

/**
 * Image d'une réponse, 1200 × 630 : l'aperçu d'un lien /r/… collé dans WhatsApp, Telegram ou un réseau social
 * (Open Graph), et l'export « Image » de la réponse (EF-36). Le chiffre, son unité, l'indicateur, la zone, la
 * période et la source, comme sur la carte réponse ; le graphique à droite quand il y en a un. Rien n'est calculé :
 * tout vient de la réponse stockée. Police de next/og (Noto Sans), couleurs du design system v2.
 */
export const TAILLE = { width: 1200, height: 630 };

const C = {
  fond: "#17110b", fond2: "#2a1f15", texte: "#f6f0e3", doux: "#bfb09a", or: "#e2bd6b", baobab: "#8cc2bc",
  ligne: "#3d2e20", evidence: "#5fc79e", neutre: "#6b5d4c",
};
// La frise de l'identité : six carrés aux couleurs fixes (tokens.css)
const FRISE = ["#1d4448", "#f6f0e3", "#a4472b", "#d9952e", "#1c140d", "#f6f0e3"];

/** Les espaces fines insécables (« 2 463 677 ») deviennent insécables simples : la police les connaît toutes. */
const net = (s: string) => s.replace(/[\u202f\u2009]/g, "\u00a0");
const court = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1).trimEnd()}…` : s);

/** Un graphique se dessine à droite : barres d'une seule série (deux barres au moins) ou courbes. */
function dessinable(r: ReponseExacte): boolean {
  const g = r.graphique;
  if (!g || g.series.length === 0) return false;
  return (g.type === "barres_horizontales" && g.series.length === 1 && g.series[0].points.length >= 2) || g.type === "courbe";
}

function Graphique({ r }: { r: ReponseExacte }) {
  const g = r.graphique;
  if (!g || !dessinable(r)) return null;
  if (g.type === "barres_horizontales") {
    const points = g.series[0]?.points ?? [];
    const visibles = points.slice(0, 7);
    for (const p of points.slice(7)) if (p.mise_en_evidence) visibles[visibles.length - 1] = p;
    const max = Math.max(...points.map((p) => p.y), 0) || 1;
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12, width: 420 }}>
        {visibles.map((p) => (
          <div key={p.x} style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ display: "flex", width: 130, justifyContent: "flex-end", fontSize: 20, color: p.mise_en_evidence ? C.texte : C.doux }}>
              {court(p.x, 14)}
            </div>
            <div style={{ display: "flex", height: 22, width: Math.max(4, (p.y / max) * 270), borderRadius: 4, background: p.mise_en_evidence ? C.evidence : C.neutre }} />
          </div>
        ))}
      </div>
    );
  }
  if (g.type === "courbe") {
    const L = 420, H = 260;
    const xs = [...new Set(g.series.flatMap((s) => s.points.map((p) => p.x)))];
    const ys = g.series.flatMap((s) => s.points.map((p) => p.y));
    const bas = Math.min(0, ...ys), haut = Math.max(...ys) || 1;
    const px = (x: string) => 10 + (xs.length > 1 ? xs.indexOf(x) / (xs.length - 1) : 0.5) * (L - 20);
    const py = (y: number) => 10 + (1 - (y - bas) / (haut - bas || 1)) * (H - 20);
    const couleurs = [C.evidence, C.or, "#e08a6a", "#8fb4d4", "#c79bd8", C.baobab];
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: L }}>
        <svg width={L} height={H} viewBox={`0 0 ${L} ${H}`}>
          <line x1={10} x2={L - 10} y1={H - 10} y2={H - 10} stroke={C.ligne} strokeWidth={2} />
          {g.series.map((s, i) => (
            <polyline key={s.nom} fill="none" stroke={couleurs[i % couleurs.length]} strokeWidth={5} strokeLinejoin="round" strokeLinecap="round"
              points={s.points.map((p) => `${px(p.x)},${py(p.y)}`).join(" ")} />
          ))}
        </svg>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 18, color: C.doux }}>
          <span>{xs[0]}</span>
          <span>{xs.at(-1)}</span>
        </div>
      </div>
    );
  }
  return null;
}

function Corps({ rep }: { rep: AskResponse | null }) {
  const r = rep?.reponse;
  if (!r || r.issue !== "exacte") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 24, flex: 1, justifyContent: "center" }}>
        {r && <div style={{ display: "flex", fontSize: 44, color: C.texte, lineHeight: 1.25 }}>{court(r.question, 110)}</div>}
        <div style={{ display: "flex", fontSize: 30, color: C.doux }}>Le chiffre officiel du Sénégal, avec sa source et sa date.</div>
      </div>
    );
  }
  const classement = r.intention === "classement" && r.resultats.length > 1;
  const affiches = classement ? [r.resultats.find((v) => v.mise_en_evidence) ?? r.resultats[0]] : r.resultats.slice(0, 3);
  const plusieurs = affiches.length > 1;
  const v = affiches[0];
  const nonObservee = r.resultats.find((x) => x.nature === "projection" || x.nature === "estimation");
  const graphique = dessinable(r);
  // Avec un graphique, le texte garde sa colonne (620 px) : sinon il passait sous les barres
  const grand = graphique ? (v.valeur_affichee.length > 9 ? 80 : 104) : v.valeur_affichee.length > 11 ? 92 : 124;
  return (
    <div style={{ display: "flex", flex: 1, gap: 32, alignItems: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", width: graphique ? 620 : 1072, gap: 14 }}>
        <div style={{ display: "flex", fontSize: 30, color: C.doux, lineHeight: 1.3 }}>{court(r.question, 90)}</div>
        {plusieurs ? (
          affiches.map((x) => (
            <div key={x.observation_id} style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
              <span style={{ fontSize: 64, color: C.or }}>{net(x.valeur_affichee)}</span>
              <span style={{ fontSize: 26, color: C.doux }}>{court(`${x.unite ? `${x.unite} · ` : ""}${x.zone.libelle} · ${x.periode.libelle}`, 40)}</span>
            </div>
          ))
        ) : (
          // Pas de fragment ici : next/og plaçait l'intitulé à droite du chiffre, sur le graphique
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 18, flexWrap: "wrap" }}>
              <span style={{ fontSize: grand, color: C.or, lineHeight: 1 }}>{net(v.valeur_affichee)}</span>
              {v.unite && <span style={{ fontSize: 36, color: C.doux }}>{court(v.unite, 30)}</span>}
            </div>
            <div style={{ display: "flex", fontSize: 28, color: C.texte, lineHeight: 1.3 }}>
              {court(`${v.indicateur.libelle} · ${v.zone.libelle} · ${v.periode.libelle}`, graphique ? 80 : 70)}
            </div>
          </div>
        )}
        {nonObservee?.nature && (
          <div style={{ display: "flex", alignSelf: "flex-start", padding: "4px 14px", borderRadius: 999, border: `2px solid ${C.ligne}`, fontSize: 22, color: C.baobab }}>
            {nonObservee.nature === "projection" ? "Projection officielle" : "Estimation officielle"}
          </div>
        )}
        <div style={{ display: "flex", fontSize: 22, color: C.doux }}>{court(`Source : ${v.source.libelle}`, 90)}</div>
      </div>
      <Graphique r={r} />
    </div>
  );
}

export function imageReponse(rep: AskResponse | null, entetes?: Record<string, string>) {
  return new ImageResponse(
    (
      <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", background: C.fond, fontFamily: "Noto Sans" }}>
        <div style={{ display: "flex", flexDirection: "column", flex: 1, padding: "48px 64px 36px", gap: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 34, color: C.texte }}>
              <div style={{ display: "flex", width: 18, height: 18, borderRadius: 999, background: C.or }} />
              Gëstukaay
            </div>
            {rep?.reponse.issue === "exacte" && (
              <div style={{ display: "flex", padding: "6px 18px", borderRadius: 999, background: C.fond2, fontSize: 22, color: C.evidence }}>
                Chiffre officiel, source citée
              </div>
            )}
          </div>
          <Corps rep={rep} />
        </div>
        <div style={{ display: "flex", height: 22 }}>
          {Array.from({ length: 12 }, (_, i) => (
            <div key={i} style={{ display: "flex", flex: 1, background: FRISE[i % FRISE.length] }} />
          ))}
        </div>
      </div>
    ),
    { ...TAILLE, headers: entetes },
  );
}
