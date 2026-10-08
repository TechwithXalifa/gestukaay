"use client";

import { useId, useState } from "react";
import type { SituateResponse } from "@contracts/situate_response";
import { useLangue } from "@/i18n/langue";
import { hautDeLAxe, pourcent } from "@/lib/situer";
import { chiffres } from "@/lib/typo";

type Ligne = { cle: string; libelle: string; valeur: number; affichee: string; periode: string };

/**
 * « Vous, votre région, le Sénégal » sur un seul axe (FCFA par personne et par an, décision 0039).
 * La fourchette du ménage est une bande (son estimation, jamais un point : elle vient de tranches) ;
 * chaque repère publié est une ligne étiquetée en toutes lettres, la couleur n'est jamais seule à
 * dire qui est qui. Le seuil de pauvreté traverse toutes les lignes. Le tableau est l'alternative.
 */
export function GraphiqueSituer({ r }: { r: SituateResponse }) {
  const { t } = useLangue();
  const id = useId();
  const [tableau, setTableau] = useState(false);
  const iv = r.depense_par_personne_an;
  const reperes: Ligne[] = [
    { cle: "region", r: r.moyenne_region },
    { cle: "pays", r: r.moyenne_pays },
    ...(r.moyenne_milieu ? [{ cle: "milieu", r: r.moyenne_milieu }] : []),
  ].map(({ cle, r: v }) => ({
    cle,
    libelle: cle === "pays" ? v.zone.libelle : cle === "region" ? v.zone.libelle : v.indicateur.libelle,
    valeur: v.valeur,
    affichee: v.valeur_affichee,
    periode: v.periode.libelle,
  }));
  const seuil = r.seuil_pauvrete;
  // tranche ouverte : la bande va jusqu'au bord de l'axe (« au moins … »)
  const max = hautDeLAxe([...reperes.map((x) => x.valeur), seuil?.valeur ?? 0, iv.maximum ?? iv.minimum * 1.25]);
  const finBande = iv.maximum ?? max;
  const graduations = [0, max / 2, max];

  return (
    <figure className="graphique graphique-situer" aria-labelledby={`${id}-titre`}>
      <div className="graphique-entete">
        <figcaption id={`${id}-titre`}>{t("situer.graphique.titre")}</figcaption>
        <button type="button" className="lien-bouton" aria-expanded={tableau} onClick={() => setTableau(!tableau)}>
          {tableau ? t("graphique.voirGraphique") : t("graphique.voirTableau", { n: String(reperes.length + 1 + (seuil ? 1 : 0)) })}
        </button>
      </div>

      {tableau ? (
        <div className="tableau-defilant">
          <table className="tableau">
            <thead>
              <tr><th scope="col">{t("situer.graphique.repere")}</th><th scope="col">{t("situer.graphique.valeur")}</th><th scope="col">{t("situer.graphique.annee")}</th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">{t("situer.graphique.vous")}</th><td>{chiffres(iv.libelle)}</td><td>{t("situer.graphique.aujourdhui")}</td></tr>
              {reperes.map((x) => (
                <tr key={x.cle}><th scope="row">{x.libelle}</th><td>{chiffres(x.affichee)} FCFA</td><td>{x.periode}</td></tr>
              ))}
              {seuil && <tr><th scope="row">{seuil.indicateur.libelle}</th><td>{chiffres(seuil.valeur_affichee)} FCFA</td><td>{seuil.periode.libelle}</td></tr>}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="situer-axe" aria-hidden="true">
          <div className="situer-ligne vous">
            <span className="situer-libelle">{t("situer.graphique.vous")}</span>
            <span className="situer-piste">
              <span className="situer-bande" style={{ left: pourcent(iv.minimum, max), width: `calc(${pourcent(finBande, max)} - ${pourcent(iv.minimum, max)})` }} />
              {seuil && <span className="situer-seuil" style={{ left: pourcent(seuil.valeur, max) }} />}
            </span>
            <span className="situer-valeur">{chiffres(iv.libelle.replace(/ par personne et par an$/, ""))}</span>
          </div>
          {reperes.map((x) => (
            <div key={x.cle} className={`situer-ligne ${x.cle}`}>
              <span className="situer-libelle">{x.libelle}</span>
              <span className="situer-piste">
                <span className="situer-point" style={{ left: pourcent(x.valeur, max) }} title={`${x.libelle} : ${x.affichee} FCFA (${x.periode})`} />
                {seuil && <span className="situer-seuil" style={{ left: pourcent(seuil.valeur, max) }} />}
              </span>
              <span className="situer-valeur">{chiffres(x.affichee)} FCFA <small>{x.periode}</small></span>
            </div>
          ))}
          {seuil && (
            <div className="situer-ligne seuil">
              <span className="situer-libelle">{seuil.indicateur.libelle}</span>
              <span className="situer-piste">
                <span className="situer-seuil fort" style={{ left: pourcent(seuil.valeur, max) }} />
              </span>
              <span className="situer-valeur">{chiffres(seuil.valeur_affichee)} FCFA <small>{seuil.periode.libelle}</small></span>
            </div>
          )}
          <div className="situer-ligne graduations">
            <span />
            <span className="situer-piste">
              {graduations.map((g) => (
                <span key={g} className="situer-graduation" style={{ left: pourcent(g, max) }}>{chiffres(Math.round(g).toLocaleString("fr-FR"))}</span>
              ))}
            </span>
            <span />
          </div>
        </div>
      )}
      <p className="graphique-pied">{t("situer.graphique.pied")}</p>
    </figure>
  );
}
