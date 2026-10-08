"use client";

import { useEffect, useRef } from "react";
import { chiffres } from "@/lib/typo";

/**
 * Chiffre qui défile jusqu'à sa valeur quand il arrive à l'écran (design system v2, « Compteur »).
 * Effet visuel de l'accueil seulement, jamais sur le chiffre d'une réponse. Le texte exact reste
 * toujours dans la page (rendu serveur, copie, lecteurs d'écran) : pendant le défilement (1,1 s),
 * il devient transparent et une copie animée, cachée aux lecteurs d'écran, passe par-dessus.
 * Rien ne bouge si moins d'animations est demandé, ou si le texte n'est pas un nombre
 * (« 1,4 s » reste tel quel) ; « 89,2 % » défile avec son signe.
 */
export function Compteur({ texte }: { texte: string }) {
  const cadre = useRef<HTMLSpanElement>(null);
  const anime = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = cadre.current;
    const copie = anime.current;
    const nombre = lire(texte);
    if (!el || !copie || nombre === null || matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) return;
    const format = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: nombre.decimales, maximumFractionDigits: nombre.decimales });
    let image = 0;
    const fin = () => {
      el.classList.remove("anime");
      copie.textContent = "";
    };
    const observateur = new IntersectionObserver(([entree]) => {
      if (!entree.isIntersecting) return;
      observateur.disconnect();
      el.classList.add("anime");
      const debut = performance.now();
      const pas = (t: number) => {
        // La première image peut porter une heure antérieure à `debut` : borné à 0 (revue de KBD)
        const p = Math.min(1, Math.max(0, (t - debut) / 1100));
        if (p === 1) return fin();
        copie.textContent = chiffres(format.format(nombre.valeur * (1 - (1 - p) ** 4))) + nombre.suffixe;
        image = requestAnimationFrame(pas);
      };
      image = requestAnimationFrame(pas);
    }, { threshold: 0.3 });
    observateur.observe(el);
    return () => {
      observateur.disconnect();
      cancelAnimationFrame(image);
      fin();
    };
  }, [texte]);

  return (
    <span ref={cadre} className="chiffre-defile">
      <span className="chiffre-defile-exact">{chiffres(texte)}</span>
      <span ref={anime} className="chiffre-defile-copie" aria-hidden="true" />
    </span>
  );
}

/** « 2 463 677 » → 2463677 ; « 20,6 » → 20,6 avec 1 décimale ; « 89,2 % » → 89,2 suivi de « % » ; autre chose → null. */
function lire(texte: string): { valeur: number; decimales: number; suffixe: string } | null {
  const morceaux = /^(-?[\d\s]+(?:,\d+)?)(\s?%)?$/.exec(texte);
  if (!morceaux) return null;
  const brut = morceaux[1].replace(/\s/g, "");
  if (!/^-?\d+(,\d+)?$/.test(brut)) return null;
  return { valeur: Number(brut.replace(",", ".")), decimales: brut.split(",")[1]?.length ?? 0, suffixe: morceaux[2] ?? "" };
}
