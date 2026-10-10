"use client";

import { useState } from "react";
import { PageTexte } from "@/components/PageTexte";
import { useLangue } from "@/i18n/langue";
import { GLOSSAIRE, normaliser } from "@/lib/glossaire";

/** Glossaire des mots de la statistique, en langage simple (« Explique-moi simplement »). Chaque mot a son
 *  ancre (/glossaire#gini) : « Comprendre ce chiffre », sous une réponse, y renvoie. */
export default function Glossaire() {
  const { t } = useLangue();
  const [q, setQ] = useState("");
  const mots = [...GLOSSAIRE]
    .sort((a, b) => a.mot.localeCompare(b.mot, "fr"))
    .filter((m) => !q.trim() || normaliser(`${m.mot} ${m.definition}`).includes(normaliser(q.trim())));
  return (
    <PageTexte titre="glossaire.titre" actif="methode">
      <p className="explication">{t("glossaire.intro")}</p>
      <div className="catalogue-filtres glossaire-filtre">
        <label htmlFor="glossaire-recherche" className="sr-only">{t("glossaire.recherche")}</label>
        <input id="glossaire-recherche" type="search" value={q} onChange={(e) => setQ(e.target.value)}
               placeholder={t("glossaire.recherche")} maxLength={60} />
      </div>
      <p className="note" role="status">
        {mots.length === 0 ? t("glossaire.aucun") : mots.length === 1 ? t("glossaire.resultat") : t("glossaire.resultats", { n: String(mots.length) })}
      </p>
      <dl className="glossaire">
        {mots.map((m) => (
          <div key={m.id} id={m.id}>
            <dt>{m.mot}</dt>
            <dd>{m.definition}</dd>
          </div>
        ))}
      </dl>
      <p className="note">{t("glossaire.note")}</p>
    </PageTexte>
  );
}
