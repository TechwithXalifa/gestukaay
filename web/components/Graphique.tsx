"use client";

import { useId, useState } from "react";
import type { ReponseExacte } from "@contracts/ask_response";
import { useLangue } from "@/i18n/langue";
import { nombre } from "@/lib/typo";
import { Baobab } from "./icones";

type G = NonNullable<ReponseExacte["graphique"]>;

/** Barres affichées avant de basculer sur le tableau (maquette Reponse : 8 barres). */
const MAX_BARRES = 8;


/**
 * Graphique de la réponse [EF-20, EF-26], dessiné côté client à partir des
 * données du contrat. Le tableau est toujours disponible : c'est l'alternative
 * textuelle [EF-28]. Le pied cite la source [EF-27].
 */
export function Graphique({ g }: { g: G }) {
  const { t } = useLangue();
  const id = useId();
  const points = g.series.flatMap((s) => s.points.map((p) => ({ ...p, serie: s.nom })));
  const dessinable = (g.type === "barres_horizontales" && g.series.length === 1) || g.type === "courbe";
  const [tableau, setTableau] = useState(!dessinable);

  return (
    <figure className="graphique" aria-labelledby={`${id}-titre`}>
      <div className="graphique-entete">
        <figcaption id={`${id}-titre`}>{g.titre}</figcaption>
        {dessinable && (
          <button type="button" className="lien-bouton" aria-expanded={tableau} onClick={() => setTableau(!tableau)}>
            {tableau ? t("graphique.voirGraphique") : t("graphique.voirTableau", { n: String(points.length) })}
          </button>
        )}
      </div>
      {tableau ? (
        <Tableau g={g} />
      ) : g.type === "courbe" ? (
        <Courbe g={g} />
      ) : (
        <Barres points={g.series[0]?.points ?? []} />
      )}
      <p className="graphique-pied"><Baobab />{g.pied}</p>
    </figure>
  );
}

function Barres({ points }: { points: G["series"][number]["points"] }) {
  // L'ordre est celui du moteur : décroissant pour un graphique de contexte, croissant pour un
  // classement « le plus faible » (ordre: asc, #14). On garde les premières, et la zone demandée
  // reste toujours visible.
  const visibles = points.slice(0, MAX_BARRES);
  for (const p of points.slice(MAX_BARRES)) if (p.mise_en_evidence) visibles[visibles.length - 1] = p;
  const max = Math.max(...points.map((p) => p.y), 0) || 1;
  return (
    <div className="barres" aria-hidden="true">
      {visibles.map((p) => (
        <div key={p.x} className={p.mise_en_evidence ? "barre en-evidence" : "barre"}>
          <span className="barre-libelle">{p.x}</span>
          <span className="barre-piste">
            <span className="barre-trait" style={{ width: `${Math.max((p.y / max) * 100, 0.5)}%` }} />
            <span className="barre-valeur">{nombre(p.y, 1)}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

const L = 600;
const H = 240;
const M = { haut: 16, bas: 28 };
const ECART_ETIQUETTES = 15; // hauteur d'une étiquette de fin de courbe, pour qu'elles ne se chevauchent pas

/** 3 à 5 graduations « rondes » (1, 2, 2,5 ou 5 × 10ⁿ) couvrant [bas, haut]. */
function graduations(bas: number, haut: number): number[] {
  const brut = (haut - bas) / 4 || 1;
  const puissance = 10 ** Math.floor(Math.log10(brut));
  const pas = [1, 2, 2.5, 5, 10].map((m) => m * puissance).find((p) => p >= brut) ?? brut;
  const ticks: number[] = [];
  const dernier = Math.ceil(haut / pas - 1e-9) * pas; // la dernière graduation couvre le maximum
  for (let v = Math.floor(bas / pas) * pas; v <= dernier + pas * 1e-9; v += pas) ticks.push(Math.round(v * 1e6) / 1e6);
  return ticks;
}

/** Positions verticales des étiquettes de fin, écartées d'au moins ECART_ETIQUETTES, sans sortir du cadre. */
function ecarter(ys: number[]): number[] {
  const ordre = ys.map((y, i) => ({ y, i })).sort((a, b) => a.y - b.y);
  for (let k = 1; k < ordre.length; k++) ordre[k].y = Math.max(ordre[k].y, ordre[k - 1].y + ECART_ETIQUETTES);
  const debord = (ordre.at(-1)?.y ?? 0) - (H - M.bas);
  if (debord > 0) for (const o of ordre) o.y -= debord;
  const sortie = new Array<number>(ys.length);
  for (const o of ordre) sortie[o.i] = Math.max(o.y, M.haut);
  return sortie;
}

/**
 * Courbes (Explorer, séries d'une réponse). Revue du 09/10 : sans légende, on ne savait pas quelle
 * courbe était quelle zone. Chaque zone a donc sa couleur ET son trait (plein, tirets, pointillés…,
 * WCAG 1.4.1), une légende au-dessus, sa dernière valeur au bout de la courbe, et l'axe est gradué.
 */
function Courbe({ g }: { g: G }) {
  const xs = [...new Set(g.series.flatMap((s) => s.points.map((p) => p.x)))];
  const ys = g.series.flatMap((s) => s.points.map((p) => p.y));
  const ticks = graduations(Math.min(0, ...ys), Math.max(...ys) || 1);
  const bas = ticks[0];
  const haut = ticks.at(-1) ?? 1;
  const derniers = g.series.map((s) => s.points.at(-1));
  // Marges à la taille des textes (≈ 7,4 unités par caractère à 12 px) : « 2 463 677 » ne sort pas du cadre
  const gauche = Math.max(...ticks.map((v) => nombre(v, 1).length)) * 7.4 + 14;
  const droite = Math.max(0, ...derniers.map((p) => (p ? nombre(p.y, 1).length : 0))) * 7.4 + 22;
  const px = (x: string) => gauche + (xs.length > 1 ? (xs.indexOf(x) / (xs.length - 1)) : 0.5) * (L - gauche - droite);
  const py = (y: number) => M.haut + (1 - (y - bas) / (haut - bas || 1)) * (H - M.haut - M.bas);
  const pas = Math.ceil(xs.length / 6);
  const positions = ecarter(derniers.map((p) => (p ? py(p.y) : 0)));
  return (
    <>
      {g.series.length > 1 && (
        <ul className="courbe-legende" aria-hidden="true">
          {g.series.map((s, i) => (
            <li key={s.nom} className={`serie serie-${i}`}>
              <svg viewBox="0 0 28 10" width="28" height="10"><line x1="1" x2="27" y1="5" y2="5" /></svg>
              {s.nom}
            </li>
          ))}
        </ul>
      )}
      <svg className="courbe" viewBox={`0 0 ${L} ${H}`} aria-hidden="true">
        {ticks.map((v) => (
          <g key={v} className="graduation">
            <line x1={gauche} x2={L - droite} y1={py(v)} y2={py(v)} className={v === bas ? "axe" : "grille"} />
            <text x={gauche - 8} y={py(v) + 4} textAnchor="end">{nombre(v, 1)}</text>
          </g>
        ))}
        {xs.map((x, i) =>
          i % pas === 0 || i === xs.length - 1 ? (
            <text key={x} x={px(x)} y={H - 8} textAnchor="middle">{x}</text>
          ) : null,
        )}
        {g.series.map((s, i) => (
          <g key={s.nom} className={`serie serie-${i}`}>
            <polyline points={s.points.map((p) => `${px(p.x)},${py(p.y)}`).join(" ")} />
            {s.points.map((p) => (
              <circle key={p.x} cx={px(p.x)} cy={py(p.y)} r={p.mise_en_evidence ? 5 : 3} />
            ))}
          </g>
        ))}
        {/* Valeur de fin, reliée à sa courbe par un trait de sa couleur quand il a fallu la décaler */}
        {derniers.map((p, i) =>
          p ? (
            <g key={g.series[i].nom} className={`serie serie-${i}`}>
              <line x1={px(p.x) + 4} y1={py(p.y)} x2={px(p.x) + 12} y2={positions[i]} className="lien-etiquette" />
              <text x={px(p.x) + 14} y={positions[i] + 4} className="etiquette">{nombre(p.y, 1)}</text>
            </g>
          ) : null,
        )}
      </svg>
    </>
  );
}

function Tableau({ g }: { g: G }) {
  const { t } = useLangue();
  const plusieurs = g.series.length > 1;
  return (
    // Zone qui défile : atteignable au clavier, et nommée pour les lecteurs d'écran
    <div className="tableau-defile" role="region" aria-label={g.titre} tabIndex={0}>
      <table className="tableau">
        <thead>
          <tr>
            {plusieurs && <th scope="col">{t("graphique.serie")}</th>}
            <th scope="col">{t("graphique.libelle")}</th>
            <th scope="col" className="nombre">{t("graphique.valeur", { unite: g.unite })}</th>
          </tr>
        </thead>
        <tbody>
          {g.series.flatMap((s) =>
            s.points.map((p) => (
              <tr key={`${s.nom}-${p.x}`} className={p.mise_en_evidence ? "en-evidence" : undefined}>
                {plusieurs && <td>{s.nom}</td>}
                <th scope="row">{p.x}</th>
                <td className="nombre">{nombre(p.y, 1)}</td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </div>
  );
}
