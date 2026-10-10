"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { useLangue } from "@/i18n/langue";
import { type Actif, ENTREE_DONNEES } from "./Entete";
import { Baobab, Croix } from "./icones";

/**
 * Barre latérale de la version mobile (maquette M-Menu, cahier 7.2) : elle s'ouvre depuis l'onglet
 * « Plus » de la barre d'onglets et regroupe la navigation, la langue et les liens du pied de page. Se ferme par
 * la croix, un toucher hors du panneau ou Échap. Fenêtre modale (WCAG 2.4.3) : le focus y entre,
 * Tab tourne dedans, et il revient sur l'onglet « Plus » à la fermeture.
 */
export function BarreLaterale({ actif, onFermer }: { actif: Actif; onFermer: () => void }) {
  const { langue, setLangue, t } = useLangue();
  const panneau = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const avant = document.activeElement as HTMLElement | null;
    panneau.current?.querySelector<HTMLElement>("button")?.focus();
    const defilement = document.body.style.overflow;
    document.body.style.overflow = "hidden"; // la page ne défile pas sous le panneau
    return () => {
      document.body.style.overflow = defilement;
      avant?.focus();
    };
  }, []);

  useEffect(() => {
    const touche = (e: KeyboardEvent) => {
      if (e.key === "Escape") onFermer();
      if (e.key !== "Tab" || !panneau.current) return;
      const focusables = [...panneau.current.querySelectorAll<HTMLElement>("a[href], button")];
      const premier = focusables[0];
      const dernier = focusables.at(-1);
      if (e.shiftKey && document.activeElement === premier) {
        e.preventDefault();
        dernier?.focus();
      } else if (!e.shiftKey && document.activeElement === dernier) {
        e.preventDefault();
        premier?.focus();
      }
    };
    window.addEventListener("keydown", touche);
    return () => window.removeEventListener("keydown", touche);
  }, [onFermer]);

  return (
    <div className="barre-laterale-fond" onClick={onFermer}>
      <div
        ref={panneau}
        className="barre-laterale"
        role="dialog"
        aria-modal="true"
        aria-label={t("nav.titreMenu")}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="barre-laterale-haut">
          <Link href="/" className="logo" onClick={onFermer}><Baobab /> <span>Gëstukaay</span></Link>
          <button type="button" className="bouton-icone" aria-label={t("nav.fermer")} onClick={onFermer}>
            <Croix />
          </button>
        </div>

        <nav aria-label={t("nav.principale")} className="barre-laterale-nav">
          <Link href="/" aria-current={actif === "question" ? "page" : undefined} onClick={onFermer}>{t("nav.demander")}</Link>
          <Link href={ENTREE_DONNEES} aria-current={actif === "donnees" ? "page" : undefined} onClick={onFermer}>{t("nav.donnees")}</Link>
          <Link href="/situer" aria-current={actif === "situer" ? "page" : undefined} onClick={onFermer}>{t("nav.situer")}</Link>
          <Link href="/methode" aria-current={actif === "methode" ? "page" : undefined} onClick={onFermer}>{t("nav.methode")}</Link>
          <Link href="/mes-chiffres" onClick={onFermer}>{t("nav.mesChiffres")}</Link>
        </nav>

        <div className="barre-laterale-langue">
          <p id="barre-langue">{t("nav.langue")}</p>
          <div role="group" aria-labelledby="barre-langue" className="bascule">
            {(["fr", "wo"] as const).map((l) => (
              <button key={l} type="button" lang={l} aria-pressed={langue === l} onClick={() => setLangue(l)}>
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <nav aria-label={t("pied.nav")} className="barre-laterale-pied">
          <Link href="/a-propos" onClick={onFermer}>{t("pied.apropos")}</Link>
          <Link href="/confidentialite" onClick={onFermer}>{t("pied.confidentialite")}</Link>
        </nav>
      </div>
    </div>
  );
}
