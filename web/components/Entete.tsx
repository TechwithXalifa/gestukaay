"use client";

import Link from "next/link";
import { useState } from "react";
import { useLangue } from "@/i18n/langue";
import { BarreLaterale } from "./BarreLaterale";
import { Baobab, Menu } from "./icones";

/** En-tête commun : logo, navigation, bascule FR/WO toujours visible (9.7). */
export function Entete({ actif = "question" }: { actif?: "question" | "situer" | null }) {
  const { langue, setLangue, t, incomplet } = useLangue();
  const [menu, setMenu] = useState(false);
  return (
    <>
      <a href="#contenu" className="evitement">{t("nav.evitement")}</a>
      <header className="entete">
        <div className="entete-int">
          {/* Mobile (< 768 px) : la navigation passe dans la barre latérale (maquette M-Menu) */}
          <button
            type="button"
            className="bouton-icone bouton-menu"
            aria-label={t("nav.menu")}
            aria-expanded={menu}
            aria-haspopup="dialog"
            onClick={() => setMenu(true)}
          >
            <Menu />
          </button>
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
      {menu && <BarreLaterale actif={actif} onFermer={() => setMenu(false)} />}
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
          <Link href="/methode">{t("pied.methode")}</Link>
          <Link href="/a-propos">{t("pied.apropos")}</Link>
          <Link href="/confidentialite">{t("pied.confidentialite")}</Link>
        </nav>
      </div>
    </footer>
  );
}
