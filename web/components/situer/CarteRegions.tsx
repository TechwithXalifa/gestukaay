"use client";

import type { SituateResponse } from "@contracts/situate_response";
import { useLangue } from "@/i18n/langue";
import { classe, TUILES } from "@/lib/situer";
import { chiffres } from "@/lib/typo";

/**
 * Consommation moyenne par tête des 14 régions (décision 0039), en tuiles placées à peu près comme sur
 * la carte. Une seule teinte, du plus clair (moyenne la plus basse) au plus foncé ; chaque tuile porte
 * sa valeur publiée, aucune borne de classe n'est affichée. Toucher une région compare le ménage à
 * celle-ci (nouvel appel à /v1/situate, rien n'est calculé ici).
 */
export function CarteRegions({ r, onRegion, occupe }: { r: SituateResponse; onRegion: (code: string) => void; occupe: boolean }) {
  const { t } = useLangue();
  const moyennes = r.moyennes_regions ?? [];
  const premiere = moyennes[0];
  if (!premiere || moyennes.length < 2) return null;
  const annee = premiere.periode.libelle;
  const valeurs = moyennes.map((m) => m.valeur);
  const ici = r.moyenne_region.zone.code;
  return (
    <section className="situer-bloc" aria-labelledby="titre-carte">
      <h2 id="titre-carte" className="sous-titre">{t("situer.carte.titre", { annee })}</h2>
      <p className="aide">{t("situer.carte.aide")}</p>
      <div className="carte-regions" role="group" aria-label={t("situer.carte.titre", { annee })}>
        {moyennes.map((m) => {
          const pos = TUILES[m.zone.code];
          if (!pos) return null;
          const c = classe(m.valeur, valeurs);
          return (
            <button
              key={m.zone.code}
              type="button"
              className={`tuile seq-${c}${m.zone.code === ici ? " ici" : ""}`}
              style={{ gridRow: pos.ligne, gridColumn: pos.colonne }}
              aria-pressed={m.zone.code === ici}
              aria-label={t("situer.carte.tuile", { region: m.zone.libelle, valeur: m.valeur_affichee })}
              // aria-disabled plutôt que disabled : la tuile garde le focus clavier pendant le calcul (revue de SAN)
              aria-disabled={occupe}
              onClick={() => !occupe && m.zone.code !== ici && onRegion(m.zone.code)}
            >
              <span className="tuile-nom">{m.zone.libelle}</span>
              <span className="tuile-valeur">{chiffres(m.valeur_affichee)}</span>
            </button>
          );
        })}
      </div>
      <div className="carte-legende" aria-hidden="true">
        <span>{t("situer.carte.basse")}</span>
        {[1, 2, 3, 4, 5].map((c) => <span key={c} className={`pastille seq-${c}`} />)}
        <span>{t("situer.carte.haute")}</span>
      </div>
      <p className="source-ligne visible discret">{premiere.source.libelle} · {t("situer.carte.unite")} · {t("situer.carte.schema")}</p>
    </section>
  );
}
