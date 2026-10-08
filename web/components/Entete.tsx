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
 */
export type Actif = "question" | "donnees" | "explorer" | "situer" | "indicateurs" | "methode" | null;

/** Explorer, Indicateurs et Domaines forment l'espace Données. */
const espace = (actif: Actif) => (actif === "explorer" || actif === "indicateurs" ? "donnees" : actif);

export function Entete({ actif = "question" }: { actif?: Actif }) {
  const { langue, setLangue, t, incomplet } = useLangue();
  const [menu, setMenu] = useState(false);
  const ici = espace(actif);
  const courant = (e: Actif) => (ici === e ? "page" : undefined);
  const bandeau = useRef<HTMLParagraphElement>(null);

  // Le bandeau « wolof en cours » tient sur 1 à 3 lignes selon la largeur : sa hauteur est mesurée
  // pour que les sections plein écran (.ecran) la retirent et ne débordent pas (revue de la PR #155)
  useEffect(() => {
    const el = bandeau.current;
    if (!el || !("ResizeObserver" in window)) return;
    const racine = document.documentElement.style;
    const mesure = new ResizeObserver(() => racine.setProperty("--hauteur-bandeau", `${el.offsetHeight}px`));
    mesure.observe(el);
    return () => {
      mesure.disconnect();
      racine.removeProperty("--hauteur-bandeau");
    };
  }, [incomplet]);

  return (
    <>
      <a href="#contenu" className="evitement">{t("nav.evitement")}</a>
      <header className="entete">
        <div className="entete-int">
          <Link href="/" className="logo">
            <Baobab /> <span>Gëstukaay</span>
          </Link>
          <nav aria-label={t("nav.principale")} className="nav">
            <Link href="/" aria-current={courant("question")}>{t("nav.demander")}</Link>
            <Link href="/indicateurs" aria-current={courant("donnees")}>{t("nav.donnees")}</Link>
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
          {ici !== "question" && <Link href="/" className="primaire bouton-poser">{t("nav.poser")}</Link>}
        </div>
      </header>
      <nav aria-label={t("nav.onglets")} className="barre-onglets">
        <Link href="/" aria-current={courant("question")}><Question taille={22} />{t("nav.demander")}</Link>
        <Link href="/indicateurs" aria-current={courant("donnees")}><Donnees taille={22} />{t("nav.donnees")}</Link>
        <Link href="/situer" aria-current={courant("situer")}><Repere taille={22} />{t("nav.meSituer")}</Link>
        <button type="button" aria-haspopup="dialog" aria-expanded={menu} onClick={() => setMenu(true)}>
          <Points taille={22} />{t("nav.plus")}
        </button>
      </nav>
      {menu && <BarreLaterale actif={ici} onFermer={() => setMenu(false)} />}
      {incomplet && <p ref={bandeau} className="bandeau-langue" role="status" lang="fr">{t("wo.enCours")}</p>}
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
          <Link href="/situer">{t("nav.situer")}</Link>
        </nav>
        <nav aria-label={t("pied.nav")}>
          <h2>{t("pied.titreConfiance")}</h2>
          <Link href="/methode">{t("pied.methode")}</Link>
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
