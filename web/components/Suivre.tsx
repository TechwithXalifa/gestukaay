"use client";

import { useId, useState } from "react";
import { useLangue } from "@/i18n/langue";
import { API_URL } from "@/lib/api";
import { REGIONS } from "@/lib/regions";
import { Copier } from "./icones";

/**
 * « Suivre les mises à jour » (fiche indicateur) : l'adresse du flux Atom de l'indicateur pour une zone. Dans un
 * lecteur de flux, ou un service qui envoie les flux par e-mail, chaque nouvelle valeur publiée prévient
 * l'usager. Gëstukaay ne garde ni adresse ni numéro : il publie seulement le flux.
 */
export function Suivre({ code, niveaux }: { code: string; niveaux: string[] }) {
  const { t } = useLangue();
  const id = useId();
  const zones = [
    ...(niveaux.includes("pays") ? [{ code: "SN", libelle: "Sénégal" }] : []),
    ...(niveaux.includes("region") || niveaux.includes("academie") ? REGIONS : []),
  ];
  const [ouvert, setOuvert] = useState(false);
  const [zone, setZone] = useState(zones[0]?.code ?? "SN");
  const [copie, setCopie] = useState<string | null>(null);
  if (zones.length === 0) return null;
  const adresse = `${API_URL}/v1/indicators/${encodeURIComponent(code)}/flux.atom?zone=${zone}`;

  return (
    <section>
      <button type="button" className="secondaire" aria-expanded={ouvert} aria-controls={id} onClick={() => setOuvert(!ouvert)}>
        {t("suivre.bouton")}
      </button>
      <div id={id} className="suivre" hidden={!ouvert}>
        <p className="aide">{t("suivre.aide")}</p>
        <div className="explorer-champ">
          <label htmlFor={`${id}-zone`}>{t("suivre.zone")}</label>
          <select id={`${id}-zone`} value={zone} onChange={(e) => setZone(e.target.value)}>
            {zones.map((z) => <option key={z.code} value={z.code}>{z.libelle}</option>)}
          </select>
        </div>
        <label htmlFor={`${id}-adresse`} className="explorer-champ">{t("suivre.adresse")}</label>
        <input id={`${id}-adresse`} className="suivre-adresse" readOnly value={adresse} onFocus={(e) => e.target.select()} />
        <div className="suivre-actions">
          <button
            type="button"
            className="secondaire"
            onClick={() => navigator.clipboard.writeText(adresse).then(() => setCopie(t("suivre.copie")), () => setCopie(t("actions.copieImpossible")))}
          >
            <Copier />{t("suivre.copier")}
          </button>
          <a className="lien" href={adresse} target="_blank" rel="noreferrer">{t("suivre.ouvrir")}</a>
        </div>
        <p className="note" role="status">{copie}</p>
        <p className="note">{t("suivre.confidentialite")}</p>
      </div>
    </section>
  );
}
