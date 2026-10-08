"use client";

import type { Resultat, SituateResponse } from "@contracts/situate_response";
import { useLangue } from "@/i18n/langue";
import { chiffres, insecables } from "@/lib/typo";
import { uniteAmbigue } from "@/lib/unites";
import { Livre } from "./icones";
import { CarteRegions } from "./situer/CarteRegions";
import { GraphiqueSituer } from "./situer/GraphiqueSituer";
import { RepartitionBienEtre } from "./situer/RepartitionBienEtre";

function Source({ v }: { v: Resultat }) {
  return (
    <p className="source-ligne visible">
      <Livre taille={16} />
      <span>{v.source.libelle}</span>
    </p>
  );
}

type Position = SituateResponse["position_region"];

/**
 * Résultat de « Où je me situe » (décisions 0004 §2, 0039). L'estimation du ménage est calculée sur
 * ses seules réponses : elle n'a JAMAIS l'apparence d'un chiffre officiel (cadre pointillé, mention
 * « votre estimation »). Les moyennes, le seuil, les groupes de bien-être et la carte sont des valeurs
 * publiées, chacune avec sa source.
 */
export function ResultatSituer({ r, onRegion, occupe = false }: {
  r: SituateResponse; onRegion?: (code: string) => void; occupe?: boolean;
}) {
  const { t } = useLangue();
  const comparaisons: { v: Resultat; position: Position; seuil?: boolean }[] = [
    { v: r.moyenne_region, position: r.position_region },
    { v: r.moyenne_pays, position: r.position_pays },
    ...(r.moyenne_milieu && r.position_milieu ? [{ v: r.moyenne_milieu, position: r.position_milieu }] : []),
    ...(r.seuil_pauvrete && r.position_seuil ? [{ v: r.seuil_pauvrete, position: r.position_seuil, seuil: true }] : []),
  ];

  return (
    <article className="carte resultat-situer" aria-labelledby="titre-resultat" aria-busy={occupe}>
      <div className="resultat-tete">
        <h1 id="titre-resultat" className="titre-situer">{t("situer.resultat")}</h1>
        <button type="button" className="secondaire petit imprimer" onClick={() => window.print()}>
          {t("situer.imprimer")}
        </button>
      </div>

      <div className="estimation">
        <p className="eyebrow-gris">{t("situer.estimation")}</p>
        <p className="valeur-estimation">{chiffres(r.depense_par_personne_an.libelle)}</p>
      </div>

      <GraphiqueSituer r={r} />

      <h2 className="sous-titre">{t("situer.comparaison")}</h2>
      <ul className="comparaisons">
        {comparaisons.map(({ v, position, seuil }) => (
          <li key={v.observation_id}>
            <p className="libelle">{v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}</p>
            <p className="valeur-petite">{chiffres(v.valeur_affichee)} <span>{v.unite}</span></p>
            <p className={`position ${position}`}>{t(seuil ? `situer.seuil.${position}` : `situer.pos.${position}`)}</p>
            <Source v={v} />
          </li>
        ))}
      </ul>

      <p className="explication">{insecables(r.explication)}</p>

      <RepartitionBienEtre r={r} />
      {onRegion && <CarteRegions r={r} onRegion={onRegion} occupe={occupe} />}

      {r.contexte.length > 0 && (
        <>
          <h2 className="sous-titre">{t("situer.contexte")}</h2>
          <ul className="contexte">
            {r.contexte.map((v) => (
              <li key={v.observation_id}>
                <span>{v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}</span>
                <strong>
                  {chiffres(v.valeur_affichee)}
                  {v.unite ? ` ${v.unite}` : uniteAmbigue(v) && <small className="sans-unite"> {t("reponse.sansUnite")}</small>}
                </strong>
                <Source v={v} />
              </li>
            ))}
          </ul>
        </>
      )}

      <aside className="encadre">
        <p><strong>{t("situer.moyenne")}</strong> {t("situer.moyenneTexte")}</p>
      </aside>
    </article>
  );
}
