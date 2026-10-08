"use client";

import type { SituateRequest } from "@contracts/situate_request";
import { useLangue } from "@/i18n/langue";
import { REGIONS } from "@/lib/regions";

export type Saisie = Pick<SituateRequest, "region" | "taille_menage" | "depenses_mensuelles" | "milieu">;
export const TRANCHES: SituateRequest["depenses_mensuelles"][] = [
  "moins_50k", "50k_100k", "100k_200k", "200k_350k", "350k_500k", "500k_750k", "750k_1m", "plus_1m",
];

/**
 * « Et si… » (décision 0039) : changer une réponse et voir la position bouger. Chaque changement rappelle
 * /v1/situate : le site ne calcule rien. Les réponses restent dans l'état de la page (US-21).
 */
export function EtSi({ saisie, onChange, occupe }: { saisie: Saisie; onChange: (s: Saisie) => void; occupe: boolean }) {
  const { t } = useLangue();
  const maj = (p: Partial<Saisie>) => onChange({ ...saisie, ...p });
  return (
    <section className="situer-bloc etsi" aria-labelledby="titre-etsi">
      <h2 id="titre-etsi" className="sous-titre">{t("situer.etsi.titre")}</h2>
      <p className="aide">{t("situer.etsi.aide")}</p>
      <div className="etsi-champs">
        <label>
          <span>{t("situer.etsi.region")}</span>
          <select value={saisie.region} onChange={(e) => maj({ region: e.target.value })}>
            {REGIONS.map((r) => <option key={r.code} value={r.code}>{r.libelle}</option>)}
          </select>
        </label>
        <label>
          <span>{t("situer.etsi.milieu")}</span>
          <select value={saisie.milieu ?? ""} onChange={(e) => maj({ milieu: (e.target.value || null) as Saisie["milieu"] })}>
            <option value="">{t("situer.milieu.aucun")}</option>
            <option value="urbain">{t("situer.milieu.urbain")}</option>
            <option value="rural">{t("situer.milieu.rural")}</option>
          </select>
        </label>
        <div className="etsi-taille">
          <span id="etsi-taille">{t("situer.etsi.taille")}</span>
          <div className="compteur petit" role="group" aria-labelledby="etsi-taille">
            <button type="button" aria-label={t("situer.moins")} disabled={saisie.taille_menage <= 1}
              onClick={() => maj({ taille_menage: saisie.taille_menage - 1 })}>−</button>
            <output aria-live="polite">{saisie.taille_menage}</output>
            <button type="button" aria-label={t("situer.plus")} disabled={saisie.taille_menage >= 40}
              onClick={() => maj({ taille_menage: saisie.taille_menage + 1 })}>+</button>
          </div>
        </div>
        <label>
          <span>{t("situer.etsi.depenses")}</span>
          <select value={saisie.depenses_mensuelles} onChange={(e) => maj({ depenses_mensuelles: e.target.value as Saisie["depenses_mensuelles"] })}>
            {TRANCHES.map((d) => <option key={d} value={d}>{t(`situer.d.${d}`)}</option>)}
          </select>
        </label>
      </div>
      <p className="discret" role="status">{occupe ? t("situer.etsi.calcul") : ""}</p>
    </section>
  );
}
