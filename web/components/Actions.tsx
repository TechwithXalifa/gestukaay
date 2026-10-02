"use client";

import { useEffect, useState } from "react";
import { useLangue } from "@/i18n/langue";
import { exportUrl } from "@/lib/api";
import { Copier, Partager, Telecharger } from "./icones";

/** Copier la citation (EF-35) et partager l'adresse stable (EF-29). Toast 3 s (9.7). */
export function Actions({ id, citation, url }: { id: string; citation: string; url: string }) {
  const { t } = useLangue();
  const [toast, setToast] = useState<string | null>(null);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  async function copier(texte: string, message: string) {
    try {
      await navigator.clipboard.writeText(texte);
      setToast(message);
    } catch {
      setToast(t("actions.copieImpossible"));
    }
  }

  async function partager() {
    if (navigator.share) {
      try {
        await navigator.share({ url });
        return;
      } catch {
        /* partage annulé : on copie le lien */
      }
    }
    copier(url, t("actions.lienCopie"));
  }

  return (
    <div className="actions">
      <a className="primaire" href={exportUrl(id, "pdf")} download>
        <Telecharger />{t("actions.pdf")}
      </a>
      <a className="secondaire" href={exportUrl(id, "csv")} download>
        <Telecharger />{t("actions.csv")}
      </a>
      <button type="button" className="secondaire" onClick={() => copier(citation, t("actions.citationCopiee"))}>
        <Copier />{t("actions.citer")}
      </button>
      <button type="button" className="secondaire" onClick={partager}>
        <Partager />{t("actions.partager")}
      </button>
      <p role="status" aria-live="polite" className={toast ? "toast visible" : "toast"}>{toast}</p>
    </div>
  );
}
