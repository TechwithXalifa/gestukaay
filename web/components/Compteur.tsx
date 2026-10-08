"use client";

import { useEffect, useRef } from "react";
import { chiffres } from "@/lib/typo";

/**
 * Chiffre qui défile jusqu'à sa valeur quand il arrive à l'écran (design system v2, « Compteur »).
 * Le texte exact est dans la page dès le premier octet (rendu serveur, copie, lecteurs d'écran) et
 * revient à la fin du défilement, qui dure 1,1 s. Rien ne bouge si moins d'animations est demandé,
 * ou si le texte n'est pas un nombre (« 1,4 s » reste tel quel).
 */
export function Compteur({ texte }: { texte: string }) {
  const visible = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = visible.current;
    const nombre = lire(texte);
    if (!el || nombre === null || matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) return;
    const format = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: nombre.decimales, maximumFractionDigits: nombre.decimales });
    let image = 0;
    const observateur = new IntersectionObserver(([entree]) => {
      if (!entree.isIntersecting) return;
      observateur.disconnect();
      const debut = performance.now();
      const pas = (t: number) => {
        const p = Math.min(1, (t - debut) / 1100);
        el.textContent = chiffres(p < 1 ? format.format(nombre.valeur * (1 - (1 - p) ** 4)) : texte);
        if (p < 1) image = requestAnimationFrame(pas);
      };
      image = requestAnimationFrame(pas);
    }, { threshold: 0.3 });
    observateur.observe(el);
    return () => {
      observateur.disconnect();
      cancelAnimationFrame(image);
      el.textContent = chiffres(texte);
    };
  }, [texte]);

  return <span ref={visible}>{chiffres(texte)}</span>;
}

/** « 2 463 677 » → 2463677, « 20,6 » → 20,6 avec 1 décimale ; autre chose → null. */
function lire(texte: string): { valeur: number; decimales: number } | null {
  const brut = texte.replace(/\s/g, "");
  if (!/^-?\d+(,\d+)?$/.test(brut)) return null;
  return { valeur: Number(brut.replace(",", ".")), decimales: brut.split(",")[1]?.length ?? 0 };
}
