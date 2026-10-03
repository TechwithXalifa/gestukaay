"use client";

import { PageTexte, Section } from "@/components/PageTexte";
import { useLangue } from "@/i18n/langue";
import type { Cle } from "@/i18n/fr";

const ETAPES = [1, 2, 3, 4, 5] as const;
const MESURES = ["bonne", "refus", "temps", "invente"] as const;

/** Méthode et transparence (maquette Methode). Les résultats chiffrés viendront du rapport de mesure (#21) :
 *  aucun chiffre de qualité n'est affiché tant qu'il n'a pas été mesuré pour de vrai. */
export default function Methode() {
  const { t } = useLangue();
  return (
    <PageTexte eyebrow="methode.eyebrow" titre="methode.titre">
      <p className="explication">{t("methode.intro")}</p>

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

      <section>
        <h2 className="sous-titre">{t("methode.mesure")}</h2>
        <p>{t("methode.mesure.intro")}</p>
        <ul className="mesures">
          {MESURES.map((m) => (
            <li key={m}>
              <strong>{t(`methode.m.${m}` as Cle)}</strong>
              <span>{t(`methode.m.${m}Cible` as Cle)}</span>
            </li>
          ))}
        </ul>
      </section>

      <p className="note">{t("methode.signaler")}</p>
    </PageTexte>
  );
}
