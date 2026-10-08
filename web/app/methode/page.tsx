"use client";

import { PageTexte, Section } from "@/components/PageTexte";
import type { Cle } from "@/i18n/fr";
import { useLangue } from "@/i18n/langue";
import { MESURE } from "@/lib/mesure";

const ETAPES = [1, 2, 3, 4, 5] as const;
const pourcent = new Intl.NumberFormat("fr-FR", { style: "percent", maximumFractionDigits: 1 });

/** Méthode et transparence (maquette Methode, cahier 12.1). Le résultat vient de lib/mesure.ts,
 *  recopié du rapport du benchmark : aucun chiffre de qualité n'est écrit à la main dans la page.
 *  Seul le taux de bonnes réponses aux tests est publié (choix de SAN du 08/10, décision 0036). */
export default function Methode() {
  const { t } = useLangue();
  const m = MESURE;

  return (
    <PageTexte titre="methode.titre" actif="methode">
      <p className="explication">{t("methode.intro")}</p>

      <section aria-labelledby="titre-mesure">
        <h2 id="titre-mesure" className="sous-titre">{t("methode.mesure")}</h2>
        <p>{t("methode.mesure.intro", { date: m.date, sur: String(m.bonne.sur) })}</p>
        <ul className="mesures-resultats">
          <li>
            <span className="mesure-titre">{t("methode.m.bonne")}</span>
            <strong>{pourcent.format(m.bonne.reussies / m.bonne.sur)}</strong>
            <span>{t("methode.m.bonneDetail", { reussies: String(m.bonne.reussies), sur: String(m.bonne.sur) })}</span>
          </li>
        </ul>
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
