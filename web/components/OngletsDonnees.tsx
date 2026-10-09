"use client";

import Link from "next/link";
import { useLangue } from "@/i18n/langue";

/** Onglets de l'espace Données (design system v2, structure) : Indicateurs (domaines compris, en filtres), Explorer. */
export function OngletsDonnees({ actif }: { actif: "indicateurs" | "explorer" }) {
  const { t } = useLangue();
  const courant = (o: typeof actif) => (actif === o ? "page" : undefined);
  return (
    <nav aria-label={t("donnees.onglets")} className="onglets-donnees">
      <Link href="/indicateurs" aria-current={courant("indicateurs")}>{t("nav.indicateurs")}</Link>
      <Link href="/explorer" aria-current={courant("explorer")}>{t("nav.explorer")}</Link>
    </nav>
  );
}
