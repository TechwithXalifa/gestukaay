"use client";

import { PageTexte } from "@/components/PageTexte";
import { useLangue } from "@/i18n/langue";

export default function APropos() {
  const { t } = useLangue();
  return (
    <PageTexte titre="apropos.titre">
      <p className="explication">{t("apropos.texte1")}</p>
      <p>{t("apropos.texte2")}</p>
      <p className="note">{t("apropos.contact")}</p>
    </PageTexte>
  );
}
