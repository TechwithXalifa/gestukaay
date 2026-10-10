"use client";

import { useEffect, useState } from "react";
import type { ReponseExacte } from "@contracts/ask_response";
import { useLangue } from "@/i18n/langue";
import { exportUrl } from "@/lib/api";
import { epingler, estEpingle, EVENEMENT, retirer } from "@/lib/favoris";
import { Copier, Partager, Signet, SignetPlein, Telecharger } from "./icones";

/**
 * Copier la citation (EF-35), partager l'adresse stable (EF-29) et épingler la réponse dans « Mes chiffres »
 * (gardée sur l'appareil seulement). Toast 3 s (9.7).
 */
export function Actions({ id, citation, url, reponse }: { id: string; citation: string; url: string; reponse?: ReponseExacte }) {
  const { t } = useLangue();
  const [toast, setToast] = useState<string | null>(null);
  const [epingle, setEpingle] = useState(false);
  useEffect(() => {
    const lire = () => setEpingle(estEpingle(id));
    lire();
    window.addEventListener(EVENEMENT, lire);
    return () => window.removeEventListener(EVENEMENT, lire);
  }, [id]);

  function basculer() {
    if (!reponse) return;
    if (epingle) {
      retirer(id);
      setToast(t("favoris.retire"));
    } else {
      setToast(t(epingler(reponse) ? "favoris.ajoute" : "favoris.impossible"));
    }
  }
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
      {/* Partager en premier et en or : la réponse se transfère d'abord sur WhatsApp (P1, US-14) */}
      <button type="button" className="primaire" onClick={partager}>
        <Partager />{t("actions.partager")}
      </button>
      <a className="secondaire" href={exportUrl(id, "pdf")} download>
        <Telecharger />{t("actions.pdf")}
      </a>
      <a className="secondaire" href={exportUrl(id, "csv")} download>
        <Telecharger />{t("actions.csv")}
      </a>
      {/* Image de la réponse (EF-36) : celle de l'aperçu de partage, servie par le site (app/r/[id]/image.png) */}
      <a className="secondaire" href={`/r/${encodeURIComponent(id)}/image.png`} download>
        <Telecharger />{t("actions.image")}
      </a>
      <button type="button" className="secondaire" onClick={() => copier(citation, t("actions.citationCopiee"))}>
        <Copier />{t("actions.citer")}
      </button>
      {reponse && (
        <button type="button" className="secondaire" aria-pressed={epingle} onClick={basculer}>
          {epingle ? <SignetPlein /> : <Signet />}{t(epingle ? "favoris.epingle" : "favoris.epingler")}
        </button>
      )}
      <p role="status" aria-live="polite" className={toast ? "toast visible" : "toast"}>{toast}</p>
    </div>
  );
}
