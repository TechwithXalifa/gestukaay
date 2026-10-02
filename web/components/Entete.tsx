"use client";

import Link from "next/link";
import { useLangue } from "@/i18n/langue";
import { Baobab } from "./icones";

/** En-tête commun : logo, navigation, bascule FR/WO toujours visible (9.7). */
export function Entete({ actif = "question" }: { actif?: "question" | "situer" }) {
  const { langue, setLangue, t, incomplet } = useLangue();
  return (
    <>
      <header className="entete">
        <div className="entete-int">
          <Link href="/" className="logo">
            <Baobab /> <span>Gëstukaay</span>
          </Link>
          <nav aria-label={t("nav.principale")} className="nav">
            <Link href="/" aria-current={actif === "question" ? "page" : undefined}>{t("nav.poser")}</Link>
            <Link href="/situer" aria-current={actif === "situer" ? "page" : undefined}>{t("nav.situer")}</Link>
          </nav>
          <div role="group" aria-label={t("langue.groupe")} className="bascule">
            {(["fr", "wo"] as const).map((l) => (
              <button key={l} type="button" lang={l} aria-pressed={langue === l} onClick={() => setLangue(l)}>
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </header>
      {incomplet && <p className="bandeau-langue" role="status" lang="fr">{t("wo.enCours")}</p>}
    </>
  );
}

export function PiedDePage({ adresse }: { adresse?: string }) {
  const { t } = useLangue();
  return (
    <footer className="pied">
      <div className="pied-int">
        <p>{adresse ? t("pied.adresse", { adresse: adresse.replace(/^https?:\/\//, "") }) : "Gëstukaay"}</p>
        <nav aria-label={t("pied.nav")}>
          <a href="#">{t("pied.methode")}</a>
          <a href="#">{t("pied.apropos")}</a>
          <a href="#">{t("pied.confidentialite")}</a>
        </nav>
      </div>
    </footer>
  );
}
