"use client";

import { useEffect, useId, useState } from "react";
import { useLangue } from "@/i18n/langue";
import { REGIONS } from "@/lib/regions";
import { Copier } from "./icones";

/**
 * « Intégrer à un site » (fiche indicateur) : le code d'un <iframe> qui affiche la dernière valeur publiée de
 * l'indicateur pour une zone, toujours à jour (app/integrer/[code]). Aperçu en direct, thème clair ou sombre.
 */
export function Integrer({ code, libelle, niveaux }: { code: string; libelle: string; niveaux: string[] }) {
  const { t } = useLangue();
  const id = useId();
  const zones = [
    ...(niveaux.includes("pays") ? [{ code: "SN", libelle: "Sénégal" }] : []),
    // Les données d'éducation par académie se lisent aussi par région (académie équivalente, décision 0003)
    ...(niveaux.includes("region") || niveaux.includes("academie") ? REGIONS : []),
  ];
  const [ouvert, setOuvert] = useState(false);
  const [zone, setZone] = useState(zones[0]?.code ?? "SN");
  const [theme, setTheme] = useState<"clair" | "sombre">("clair");
  const [origine, setOrigine] = useState("");
  const [copie, setCopie] = useState<string | null>(null);
  useEffect(() => setOrigine(window.location.origin), []);
  if (zones.length === 0) return null;

  const src = `${origine}/integrer/${encodeURIComponent(code)}?zone=${zone}${theme === "sombre" ? "&theme=sombre" : ""}`;
  const html = `<iframe src="${src}" title="${libelle.replace(/"/g, "&quot;")} · Gëstukaay" width="420" height="200" style="border:0" loading="lazy"></iframe>`;

  async function copier() {
    try {
      await navigator.clipboard.writeText(html);
      setCopie(t("integrer.copie"));
    } catch {
      setCopie(t("actions.copieImpossible"));
    }
  }

  return (
    <section>
      <button type="button" className="secondaire" aria-expanded={ouvert} aria-controls={id} onClick={() => setOuvert(!ouvert)}>
        {t("integrer.bouton")}
      </button>
      <div id={id} className="integrer" hidden={!ouvert}>
        <p className="aide">{t("integrer.aide")}</p>
        <div className="integrer-reglages">
          <div className="explorer-champ">
            <label htmlFor={`${id}-zone`}>{t("integrer.zone")}</label>
            <select id={`${id}-zone`} value={zone} onChange={(e) => setZone(e.target.value)}>
              {zones.map((z) => <option key={z.code} value={z.code}>{z.libelle}</option>)}
            </select>
          </div>
          <div className="explorer-champ">
            <label htmlFor={`${id}-theme`}>{t("integrer.theme")}</label>
            <select id={`${id}-theme`} value={theme} onChange={(e) => setTheme(e.target.value as "clair" | "sombre")}>
              <option value="clair">{t("integrer.clair")}</option>
              <option value="sombre">{t("integrer.sombre")}</option>
            </select>
          </div>
        </div>
        {ouvert && origine && <iframe src={src} title={t("integrer.apercu", { libelle })} loading="lazy" />}
        <label htmlFor={`${id}-code`} className="explorer-champ">{t("integrer.code")}</label>
        <textarea id={`${id}-code`} readOnly value={html} onFocus={(e) => e.target.select()} />
        <div>
          <button type="button" className="secondaire" onClick={copier}><Copier />{t("integrer.copier")}</button>
          <p className="note" role="status">{copie}</p>
        </div>
      </div>
    </section>
  );
}
