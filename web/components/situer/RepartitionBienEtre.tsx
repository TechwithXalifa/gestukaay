"use client";

import type { SituateResponse } from "@contracts/situate_response";
import { useLangue } from "@/i18n/langue";
import { chiffres } from "@/lib/typo";

/**
 * Part de la population de la région dans chacun des cinq groupes de bien-être (décision 0039).
 * Barre empilée à 100 %, une seule teinte du plus clair (groupe le plus bas) au plus foncé : les
 * groupes sont ordonnés. Le ménage n'y est PAS placé : les seuils des groupes ne sont pas publiés.
 * La liste en dessous est la légende et l'alternative textuelle.
 */
export function RepartitionBienEtre({ r }: { r: SituateResponse }) {
  const { t } = useLangue();
  const groupes = r.repartition_bien_etre ?? [];
  if (groupes.length !== 5) return null;
  const g0 = groupes[0];
  return (
    <section className="situer-bloc" aria-labelledby="titre-repartition">
      <h2 id="titre-repartition" className="sous-titre">{t("situer.repartition.titre", { region: g0.zone.libelle })}</h2>
      <p className="aide">{t("situer.repartition.aide")}</p>
      <div className="repartition-barre" aria-hidden="true">
        {groupes.map((g, i) => (
          <span key={g.observation_id} className={`seq-${i + 1}`} style={{ flexGrow: g.valeur }} title={`${g.indicateur.libelle} : ${g.valeur_affichee} %`} />
        ))}
      </div>
      <ol className="repartition-liste">
        {groupes.map((g, i) => (
          <li key={g.observation_id}>
            <span className={`pastille seq-${i + 1}`} aria-hidden="true" />
            <span>{g.indicateur.libelle}</span>
            <strong>{chiffres(g.valeur_affichee)} %</strong>
          </li>
        ))}
      </ol>
      <p className="source-ligne visible discret">{g0.source.libelle} · {g0.periode.libelle}</p>
    </section>
  );
}
