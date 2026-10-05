"use client";

import { useEffect, useRef } from "react";
import { useLangue } from "@/i18n/langue";
import { ErreurApi } from "@/lib/api";
import { Coche, Tourne } from "./icones";

/** Chargement : étapes visibles et squelettes, jamais un spinner seul (7.3). */
export function Chargement({ question }: { question?: string }) {
  const { t } = useLangue();
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    // Sur l'accueil, les étapes s'affichent sous les exemples : on les amène à l'écran si besoin
    const doux = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    ref.current?.scrollIntoView?.({ block: "nearest", behavior: doux ? "smooth" : "auto" });
  }, []);
  return (
    <section ref={ref} className="carte" aria-busy="true" aria-live="polite">
      <ol className="etapes">
        <li className="fait"><Coche />{t("etat.recue")}{question ? ` : « ${question} »` : ""}</li>
        <li className="encours"><Tourne />{t("etat.recherche")}</li>
      </ol>
      <div aria-hidden="true" className="squelettes">
        <div style={{ width: "42%", height: 12 }} />
        <div style={{ width: "66%", height: 44 }} />
        <div style={{ height: 120 }} />
      </div>
    </section>
  );
}

/** Hors ligne et erreur système : message humain, Réessayer, code discret (7.3). */
export function Erreur({ erreur, onReessayer }: { erreur: unknown; onReessayer: () => void }) {
  const { t } = useLangue();
  const e = erreur instanceof ErreurApi ? erreur : null;
  if (e?.statut === 404)
    return (
      <section className="carte">
        <h1 className="titre-etat">{t("etat.introuvable")}</h1>
        <p className="explication">{t("etat.introuvableAide")}</p>
      </section>
    );
  return (
    <section className="carte" role="alert">
      <h1 className="titre-etat">{t(e?.horsLigne ? "horsligne.titre" : "etat.service")}</h1>
      <p className="explication">
        {t(e?.horsLigne ? "horsligne.aide" : "etat.serviceAide")}
      </p>
      <button type="button" className="primaire" onClick={onReessayer}>{t("etat.reessayer")}</button>
      {e?.codeIncident && <p className="note">{t("etat.incident", { code: e.codeIncident })}</p>}
    </section>
  );
}
