"use client";

import Link from "next/link";
import { PageTexte } from "@/components/PageTexte";
import { useLangue } from "@/i18n/langue";

/**
 * Erreur système dans une page (7.3) : message humain, Réessayer, code discret, jamais de trace
 * technique. `digest` est l'identifiant que Next écrit aussi dans les journaux du serveur.
 */
export default function ErreurPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const { t } = useLangue();
  return (
    <PageTexte titre="etat.service">
      <p className="explication">{t("etat.erreurAide")}</p>
      <div className="actions">
        <button type="button" className="primaire" onClick={reset}>{t("etat.reessayer")}</button>
        <Link href="/" className="secondaire">{t("etat.accueil")}</Link>
      </div>
      {error.digest && <p className="note">{t("etat.incident", { code: error.digest })}</p>}
    </PageTexte>
  );
}
