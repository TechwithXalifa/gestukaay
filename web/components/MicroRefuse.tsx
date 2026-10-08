"use client";

import { useEffect, useRef } from "react";
import { useLangue } from "@/i18n/langue";
import { Cadenas, MicroBarre } from "./icones";

/** État « Micro refusé » (7.3, maquette M-MicroRefuse) : 2 étapes + la saisie texte reste possible. */
export function MicroRefuse({ onReessayer }: { onReessayer: () => void }) {
  const { t } = useLangue();
  const site = typeof window !== "undefined" ? window.location.host : "ce site";
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    // Sur l'accueil, le message s'affiche sous le héros plein écran : on l'amène à l'écran
    const doux = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    ref.current?.scrollIntoView?.({ block: "nearest", behavior: doux ? "smooth" : "auto" });
  }, []);
  return (
    <section ref={ref} className="carte micro-refuse" role="alert">
      <span className="pastille-icone"><MicroBarre taille={24} /></span>
      <h1 className="titre-etat">{t("micro.titre", { site })}</h1>
      <p className="explication">{t("micro.intro")}</p>
      <ol className="etapes-numerotees">
        <li><span aria-hidden="true">1</span><span>{t("micro.etape1")}</span></li>
        <li><span aria-hidden="true">2</span><span>{t("micro.etape2")}</span></li>
      </ol>
      <button type="button" className="primaire" onClick={onReessayer}>{t("micro.reessayer")}</button>
      <p className="note"><Cadenas taille={16} />{t("micro.texte")}</p>
    </section>
  );
}
