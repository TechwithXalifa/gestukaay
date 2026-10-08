"use client";

import { Coche } from "@/components/icones";
import { PageTexte, Section } from "@/components/PageTexte";
import type { Cle } from "@/i18n/fr";
import { useLangue } from "@/i18n/langue";
import { MESURE } from "@/lib/mesure";

const ETAPES = [1, 2, 3, 4, 5] as const;
const pourcent = new Intl.NumberFormat("fr-FR", { style: "percent", maximumFractionDigits: 1 });
const secondes = (ms: number) => `${(ms / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} s`;

/** Méthode et transparence (maquette Methode, cahier 12.1). Les résultats viennent de lib/mesure.ts,
 *  recopié du rapport du benchmark : aucun chiffre de qualité n'est écrit à la main dans la page. */
export default function Methode() {
  const { t } = useLangue();
  const m = MESURE;
  const mesures: { cle: string; valeur: string; detail: string; cible: Cle; atteint: boolean }[] = [
    {
      cle: "bonne",
      valeur: pourcent.format(m.bonne.reussies / m.bonne.sur),
      detail: t("methode.m.bonneDetail", { reussies: String(m.bonne.reussies), sur: String(m.bonne.sur) }),
      cible: "methode.m.bonneCible",
      atteint: m.bonne.reussies / m.bonne.sur >= 0.85,
    },
    {
      cle: "refus",
      valeur: pourcent.format(m.refus.reussis / m.refus.sur),
      detail: t("methode.m.refusDetail", { reussis: String(m.refus.reussis), sur: String(m.refus.sur) }),
      cible: "methode.m.refusCible",
      atteint: m.refus.reussis / m.refus.sur >= 0.95,
    },
    {
      cle: "temps",
      valeur: secondes(m.latence.medianeMs),
      detail: t("methode.m.tempsDetail", { mediane: secondes(m.latence.medianeMs), p95: secondes(m.latence.p95Ms) }),
      cible: "methode.m.tempsCible",
      atteint: m.latence.medianeMs < 3000,
    },
    {
      cle: "invente",
      valeur: String(m.inventes),
      detail: t("methode.m.inventeDetail"),
      cible: "methode.m.inventeCible",
      atteint: m.inventes === 0,
    },
  ];
  const langues: { libelle: Cle; r?: { reussies: number; sur: number } }[] = [
    { libelle: "methode.fr", r: m.langues.fr },
    { libelle: "methode.wo", r: m.langues.wo },
    { libelle: "methode.voix" },
  ];
  const erreurs: [Cle, number][] = [
    ["methode.e.approchees", m.erreurs.approcheesEnRefus],
    ["methode.e.horsSujet", m.erreurs.horsSujet],
    ["methode.e.sansReponse", m.erreurs.sansReponse],
  ];

  return (
    <PageTexte titre="methode.titre" actif="methode">
      <p className="explication">{t("methode.intro")}</p>

      <section aria-labelledby="titre-mesure">
        <h2 id="titre-mesure" className="sous-titre">{t("methode.mesure")}</h2>
        <p>{t("methode.mesure.intro", { date: m.date, n: String(m.questions.total), fr: String(m.questions.fr), wo: String(m.questions.wo) })}</p>
        <ul className="mesures-resultats">
          {mesures.map((x) => (
            <li key={x.cle}>
              <span className="mesure-titre">{t(`methode.m.${x.cle}` as Cle)}</span>
              <strong>{x.valeur}</strong>
              <span>{x.detail}</span>
              <span className={x.atteint ? "mesure-cible atteinte" : "mesure-cible"}>
                {x.atteint && <Coche taille={14} />}{t(x.cible)}{x.atteint ? ` · ${t("methode.atteint")}` : ""}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 id="titre-langues" className="sous-titre">{t("methode.langues")}</h2>
        <div className="tableau-defile" role="region" aria-labelledby="titre-langues" tabIndex={0}>
          <table className="tableau">
            <thead>
              <tr><th scope="col">{t("methode.langue")}</th><th scope="col" className="nombre">{t("methode.reussite")}</th></tr>
            </thead>
            <tbody>
              {langues.map(({ libelle, r }) => (
                <tr key={libelle}>
                  <th scope="row">{t(libelle)}</th>
                  <td className="nombre">{r ? `${pourcent.format(r.reussies / r.sur)} (${r.reussies}/${r.sur})` : t("methode.voixPasEncore")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="titre-erreurs">
        <h2 id="titre-erreurs" className="sous-titre">{t("methode.erreurs")}</h2>
        <ul className="mesures-erreurs">
          {erreurs.map(([cle, n]) => (
            <li key={cle}><span>{t(cle)}</span><strong>{t("methode.e.questions", { n: String(n) })}</strong></li>
          ))}
        </ul>
        <p className="note">{t("methode.e.note")}</p>
      </section>

      <section>
        <h2 className="sous-titre">{t("methode.etapes")}</h2>
        <ol className="etapes">
          {ETAPES.map((n) => (
            <li key={n}>
              <strong>{t(`methode.e${n}.titre` as Cle)}</strong>
              <span>{t(`methode.e${n}.texte` as Cle)}</span>
            </li>
          ))}
        </ol>
      </section>

      <Section titre="methode.donnees" textes={["methode.donnees.texte", "methode.projections", "methode.corrections"]} />

      <p className="note">{t("methode.signaler")}</p>
    </PageTexte>
  );
}
