"use client";

import { useId, useState } from "react";
import type { ReponseExacte } from "@contracts/ask_response";
import { useLangue } from "@/i18n/langue";
import { Baobab } from "./icones";

type G = NonNullable<ReponseExacte["graphique"]>;

/** Barres affichées avant de basculer sur le tableau (maquette Reponse : 8 barres). */
const MAX_BARRES = 8;

const nombre = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

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
            <span className="barre-valeur">{nombre.format(p.y)}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

const L = 600;
const H = 220;
const M = { haut: 16, droite: 16, bas: 28, gauche: 16 };

function Courbe({ g }: { g: G }) {
  const xs = [...new Set(g.series.flatMap((s) => s.points.map((p) => p.x)))];
  const ys = g.series.flatMap((s) => s.points.map((p) => p.y));
  const bas = Math.min(0, ...ys);
  const haut = Math.max(...ys) || 1;
  const px = (x: string) => M.gauche + (xs.length > 1 ? (xs.indexOf(x) / (xs.length - 1)) : 0.5) * (L - M.gauche - M.droite);
  const py = (y: number) => M.haut + (1 - (y - bas) / (haut - bas)) * (H - M.haut - M.bas);
  const pas = Math.ceil(xs.length / 6);
  return (
    <svg className="courbe" viewBox={`0 0 ${L} ${H}`} aria-hidden="true">
      <line x1={M.gauche} x2={L - M.droite} y1={H - M.bas} y2={H - M.bas} className="axe" />
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
      {(() => {
        const dernier = g.series[0]?.points.at(-1);
        return dernier ? (
          <text x={px(dernier.x)} y={py(dernier.y) - 10} textAnchor="end" className="etiquette">
            {nombre.format(dernier.y)}
          </text>
        ) : null;
      })()}
    </svg>
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
                <td className="nombre">{nombre.format(p.y)}</td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </div>
  );
}
