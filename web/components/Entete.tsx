"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useLangue } from "@/i18n/langue";
import { BarreLaterale } from "./BarreLaterale";
import { Baobab, Donnees, Points, Question, Repere } from "./icones";

/**
 * En-tête commun (design system v2) : logo, trois espaces et la Méthode, bascule FR/WO toujours
 * visible (9.7). Sous 768 px, la navigation passe dans une barre d'onglets en bas de l'écran ;
 * « Plus » ouvre la barre latérale (maquette M-Menu).
 * L'en-tête flotte en pilule au-dessus de la page (inspiré d'adafrik.com) : il glisse hors de
 * l'écran quand on descend et revient dès qu'on remonte. Il reste visible en haut de page, menu
 * ouvert, quand le focus clavier y entre, et toujours si moins d'animations est demandé (CSS).
 */
export type Actif = "question" | "donnees" | "explorer" | "situer" | "indicateurs" | "zones" | "methode" | null;

/** Explorer, Indicateurs et Domaines forment l'espace Données. */

/** Entrée de l'espace Données (en-tête, menu) : le catalogue, servi par le moteur réel depuis #156. */
export const ENTREE_DONNEES = "/indicateurs";
const espace = (actif: Actif) => (actif === "explorer" || actif === "indicateurs" || actif === "zones" ? "donnees" : actif);

export function Entete({ actif = "question" }: { actif?: Actif }) {
  const { langue, setLangue, t } = useLangue();
  const [menu, setMenu] = useState(false);
  const ici = espace(actif);
  const courant = (e: Actif) => (ici === e ? "page" : undefined);
  const entete = useRef<HTMLElement>(null);
  const [cache, setCache] = useState(false);

  // Place prise en haut de page par l'en-tête flottant, bandeau « wolof en cours » compris (1 à 3
  // lignes selon la largeur) : le contenu et les sections plein écran commencent dessous.
  useEffect(() => {
    const el = entete.current;
    if (!el || !("ResizeObserver" in window)) return;
    const racine = document.documentElement.style;
    const mesure = new ResizeObserver(() => racine.setProperty("--hauteur-entete", `${el.offsetTop + el.offsetHeight}px`));
    mesure.observe(el);
    return () => {
      mesure.disconnect();
      racine.removeProperty("--hauteur-entete");
    };
  }, []);

  // Descendre cache l'en-tête, remonter le fait revenir ; un petit seuil ignore les tremblements.
  // Le navigateur envoie au plus un « scroll » par image, et React ignore un état inchangé.
  useEffect(() => {
    let dernier = window.scrollY;
    const defiler = () => {
      const y = window.scrollY;
      if (y < 80) {
        setCache(false);
        dernier = y;
      } else if (Math.abs(y - dernier) > 8) {
        setCache(y > dernier);
        dernier = y;
      }
    };
    window.addEventListener("scroll", defiler, { passive: true });
    return () => window.removeEventListener("scroll", defiler);
  }, []);

  return (
    <>
      <a href="#contenu" className="evitement">{t("nav.evitement")}</a>
      <header ref={entete} className={cache && !menu ? "entete cache" : "entete"}>
        <div className="entete-int">
          <Link href="/" className="logo">
            <Baobab /> <span>Gëstukaay</span>
          </Link>
          <nav aria-label={t("nav.principale")} className="nav">
            <Link href="/" aria-current={courant("question")}>{t("nav.poser")}</Link>
            <Link href={ENTREE_DONNEES} aria-current={courant("donnees")}>{t("nav.donnees")}</Link>
            <Link href="/situer" aria-current={courant("situer")}>{t("nav.situer")}</Link>
            <Link href="/methode" aria-current={courant("methode")}>{t("nav.methode")}</Link>
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
      <nav aria-label={t("nav.onglets")} className="barre-onglets">
        <Link href="/" aria-current={courant("question")}><Question taille={22} />{t("nav.demander")}</Link>
        <Link href={ENTREE_DONNEES} aria-current={courant("donnees")}><Donnees taille={22} />{t("nav.donnees")}</Link>
        <Link href="/situer" aria-current={courant("situer")}><Repere taille={22} />{t("nav.meSituer")}</Link>
        <button type="button" aria-haspopup="dialog" aria-expanded={menu} onClick={() => setMenu(true)}>
          <Points taille={22} />{t("nav.plus")}
        </button>
      </nav>
      {menu && <BarreLaterale actif={ici} onFermer={() => setMenu(false)} />}
    </>
  );
}

export function PiedDePage({ adresse }: { adresse?: string }) {
  const { t } = useLangue();
  return (
    <footer className="pied">
      <div className="pied-int">
        <div>
          <Link href="/" className="logo"><Baobab /> <span>Gëstukaay</span></Link>
          <p>{t("pied.promesse")}</p>
        </div>
        <nav aria-label={t("pied.navDonnees")}>
          <h2>{t("pied.titreDonnees")}</h2>
          <Link href="/">{t("nav.poser")}</Link>
          <Link href="/indicateurs">{t("nav.indicateurs")}</Link>
          <Link href="/explorer">{t("nav.explorer")}</Link>
          <Link href="/zones">{t("nav.zones")}</Link>
          <Link href="/situer">{t("nav.situer")}</Link>
        </nav>
        <nav aria-label={t("pied.nav")}>
          <h2>{t("pied.titreConfiance")}</h2>
          <Link href="/mes-chiffres">{t("nav.mesChiffres")}</Link>
          <Link href="/methode">{t("pied.methode")}</Link>
          <Link href="/glossaire">{t("pied.glossaire")}</Link>
          <Link href="/developpeurs">{t("pied.api")}</Link>
          <Link href="/a-propos">{t("pied.apropos")}</Link>
          <Link href="/confidentialite">{t("pied.confidentialite")}</Link>
        </nav>
      </div>
      <div className="pied-bas">
        <p>{adresse ? t("pied.adresse", { adresse: adresse.replace(/^https?:\/\//, "") }) : t("pied.donnees")}</p>
      </div>
    </footer>
  );
}
