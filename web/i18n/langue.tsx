"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { type Cle, fr } from "./fr";
import { wo } from "./wo";

export type Langue = "fr" | "wo";
type T = (cle: Cle, vars?: Record<string, string>) => string;
type Ctx = { langue: Langue; setLangue: (l: Langue) => void; t: T; incomplet: boolean };

const CLE = "gestukaay.langue";
const LangueCtx = createContext<Ctx | null>(null);

/** Langue de l'interface (EF-12 : l'utilisateur choisit) — pas celle de la question. */
export function LangueProvider({ children }: { children: React.ReactNode }) {
  const [langue, setEtat] = useState<Langue>("fr");

  useEffect(() => {
    try {
      if (localStorage.getItem(CLE) === "wo") setEtat("wo");
    } catch {
      /* stockage bloqué : français par défaut */
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.langue = langue; // repris par le CSS de la bascule (layout.tsx)
    // lang n'est mis à « wo » que si l'interface est réellement en wolof
    document.documentElement.lang = langue === "wo" && Object.keys(wo).length > 0 ? "wo" : "fr";
  }, [langue]);

  const setLangue = useCallback((l: Langue) => {
    setEtat(l);
    try {
      localStorage.setItem(CLE, l);
    } catch {
      /* préférence non retenue, sans gravité */
    }
  }, []);

  const t = useCallback<T>(
    (cle, vars) => {
      const texte = (langue === "wo" && wo[cle]) || fr[cle];
      return vars ? texte.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "") : texte;
    },
    [langue],
  );

  const incomplet = langue === "wo" && Object.keys(wo).length < Object.keys(fr).length;
  return <LangueCtx.Provider value={{ langue, setLangue, t, incomplet }}>{children}</LangueCtx.Provider>;
}

export function useLangue(): Ctx {
  const c = useContext(LangueCtx);
  if (!c) throw new Error("useLangue hors de LangueProvider");
  return c;
}
