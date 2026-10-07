"use client";

import Link from "next/link";
import { PageTexte } from "@/components/PageTexte";
import { useLangue } from "@/i18n/langue";

/** Adresse inconnue : la page de Next était en anglais et sans en-tête. Aucune impasse (7.1 n° 7). */
export default function PageIntrouvable() {
  const { t } = useLangue();
  return (
    <PageTexte eyebrow="etat.erreur404" titre="etat.pageIntrouvable">
      <p className="explication">{t("etat.pageIntrouvableAide")}</p>
      <div className="actions">
        <Link href="/" className="primaire">{t("etat.accueil")}</Link>
        <Link href="/domaines" className="secondaire">{t("etat.domaines")}</Link>
      </div>
    </PageTexte>
  );
}
