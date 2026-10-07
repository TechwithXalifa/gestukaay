"use client";

import type { Resultat, SituateResponse } from "@contracts/situate_response";
import { useLangue } from "@/i18n/langue";
import { insecables } from "@/lib/typo";
import { Livre } from "./icones";

function Source({ v }: { v: Resultat }) {
  return (
    <p className="source-ligne visible">
      <Livre taille={16} />
      <span>{v.source.libelle}</span>
    </p>
  );
}

/**
 * Résultat de « Où je me situe » (décision 0004 §2). L'estimation du ménage
 * est calculée sur ses seules réponses : elle n'a JAMAIS l'apparence d'un
 * chiffre officiel (cadre pointillé, mention « votre estimation »). Les
 * moyennes et repères sont des valeurs publiées, chacune avec sa source.
 */
export function ResultatSituer({ r }: { r: SituateResponse }) {
  const { t } = useLangue();
  const comparaisons = [
    { v: r.moyenne_region, position: r.position_region },
    { v: r.moyenne_pays, position: r.position_pays },
  ];

  return (
    <article className="carte resultat-situer" aria-labelledby="titre-resultat">
      <h1 id="titre-resultat" className="titre-situer">{t("situer.resultat")}</h1>

      <div className="estimation">
        <p className="eyebrow-gris">{t("situer.estimation")}</p>
        <p className="valeur-estimation">{r.depense_par_personne_an.libelle}</p>
      </div>

      <h2 className="sous-titre">{t("situer.comparaison")}</h2>
      <ul className="comparaisons">
        {comparaisons.map(({ v, position }) => (
          <li key={v.observation_id}>
            <p className="libelle">{v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}</p>
            <p className="valeur-petite">{v.valeur_affichee} <span>{v.unite}</span></p>
            <p className={`position ${position}`}>{t(`situer.pos.${position}`)}</p>
            <Source v={v} />
          </li>
        ))}
      </ul>

      <p className="explication">{insecables(r.explication)}</p>

      {r.contexte.length > 0 && (
        <>
          <h2 className="sous-titre">{t("situer.contexte")}</h2>
          <ul className="contexte">
            {r.contexte.map((v) => (
              <li key={v.observation_id}>
                <span>{v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}</span>
                <strong>
                  {v.valeur_affichee}
                  {v.unite ? ` ${v.unite}` : <small className="sans-unite"> {t("reponse.sansUnite")}</small>}
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
