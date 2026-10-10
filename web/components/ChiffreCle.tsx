"use client";

import Link from "next/link";
import { useLangue } from "@/i18n/langue";
import type { ValeurCle } from "@/lib/api";
import { chiffres } from "@/lib/typo";
import { ordinal } from "@/lib/zones";
import { Donnees, Livre, Tendance } from "./icones";

/**
 * Un chiffre clé de « Ma région en chiffres » : le libellé, la valeur publiée et son unité, la période, le rang
 * parmi les régions (un tri des valeurs publiées) et la source. Une projection ou une estimation officielle
 * porte son badge (décision 0002), comme sur une réponse.
 */
export function ChiffreCle({ c, zone }: { c: ValeurCle; zone: string }) {
  const { t } = useLangue();
  const nonObservee = c.nature === "projection" || c.nature === "estimation";
  // L'école est publiée par académie : le rang se lit parmi les académies
  const vars = { sur: String(c.sur), zones: t(c.zone_servie.niveau === "academie" ? "zone.academies" : "zone.regions") };
  const rang =
    c.rang && c.sur
      ? c.rang === 1
        ? t("zone.rangPremier", vars)
        : c.rang === c.sur
          ? t("zone.rangDernier", vars)
          : t("zone.rang", { ...vars, rang: ordinal(c.rang) })
      : null;
  const zones = zone === "SN" ? "SN" : `SN,${zone}`;
  return (
    <li className="chiffre-cle">
      <h3>{c.indicateur.libelle}</h3>
      <p className={c.valeur_affichee.length > 11 ? "chiffre-cle-valeur longue" : "chiffre-cle-valeur"}>
        <span>{chiffres(c.valeur_affichee)}</span> <span className="unite">{c.unite}</span>
      </p>
      <p className="chiffre-cle-periode">
        {t("zone.en", { periode: c.libelle_periode })}
        {c.zone_servie.niveau === "academie" && ` · ${c.zone_servie.libelle}`}
        {nonObservee && (
          <span className="badge projection">
            <Tendance taille={14} />{t(c.nature === "projection" ? "reponse.projection" : "reponse.estimation")}
          </span>
        )}
      </p>
      {rang && <p className="chiffre-cle-rang">{rang}</p>}
      <p className="source-ligne"><Livre taille={16} /><span>{c.source.libelle}</span></p>
      <Link className="lien" href={`/explorer?indicateur=${encodeURIComponent(c.indicateur.code)}&zones=${zones}`}>
        <Donnees taille={16} />{t("zone.explorer")}
      </Link>
    </li>
  );
}
