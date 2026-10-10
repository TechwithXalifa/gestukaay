"use client";

import { useEffect, useState } from "react";
import { useLangue } from "@/i18n/langue";
import { carte, type CarteResponse } from "@/lib/api";
import { REGIONS } from "@/lib/regions";
import { classe, TUILES } from "@/lib/situer";
import { chiffres, titreSource } from "@/lib/typo";
import { Chargement, Erreur } from "./Etats";
import { Livre } from "./icones";

const nomRegion = (code: string) => REGIONS.find((r) => r.code === code)?.libelle ?? code;

/**
 * Explorer, vue « Carte » : les 14 régions en tuiles placées à peu près comme sur la carte (même schéma que
 * « Où je me situe », décision 0039), une seule teinte du plus clair (plus basse) au plus foncé (plus élevée).
 * Chaque tuile porte sa valeur publiée ; une région qui ne publie pas la période est en pointillés, jamais
 * estimée. Toucher une tuile l'ajoute aux zones comparées (ou l'en retire) : le graphique la montre ensuite.
 */
export function CarteExplorer({
  indicateur,
  periode,
  choisies,
  onPeriode,
  onZone,
}: {
  indicateur: string;
  periode: string;
  choisies: string[];
  onPeriode: (periode: string) => void;
  onZone: (code: string) => void;
}) {
  const { t } = useLangue();
  const [r, setR] = useState<CarteResponse | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [essai, setEssai] = useState(0);

  useEffect(() => {
    let annule = false;
    setErreur(null);
    carte(indicateur, periode || undefined)
      .then((x) => !annule && setR(x))
      .catch((e) => !annule && setErreur(e));
    return () => {
      annule = true;
    };
  }, [indicateur, periode, essai]);

  if (erreur) return <Erreur erreur={erreur} onReessayer={() => setEssai((n) => n + 1)} />;
  if (!r) return <Chargement />;

  const valeurs = r.valeurs.map((v) => v.valeur);
  const academies = r.valeurs.some((v) => v.zone.niveau === "academie");
  const nonObservee = r.valeurs.some((v) => v.nature === "projection" || v.nature === "estimation");
  const titre = t("carte.titre", { indicateur: r.indicateur.libelle, periode: r.libelle_periode ?? "" });

  return (
    <section className="carte-explorer" aria-labelledby="titre-carte-explorer">
      <div className="carte-explorer-tete">
        <h2 id="titre-carte-explorer" className="graphique-titre">{titre}</h2>
        {r.periodes.length > 1 && (
          <div className="explorer-champ">
            <label htmlFor="carte-periode">{t("carte.periode")}</label>
            <select id="carte-periode" value={r.periode ?? ""} onChange={(e) => onPeriode(e.target.value)}>
              {r.periodes.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        )}
      </div>

      {r.valeurs.length < 2 ? (
        <p className="explication">{t(r.valeurs.length ? "carte.une" : "carte.aucune")}</p>
      ) : (
        <>
          <p className="aide">{t("carte.aide")}</p>
          <div className="carte-regions" role="group" aria-label={titre}>
            {REGIONS.map(({ code }) => {
              const pos = TUILES[code];
              const v = r.valeurs.find((x) => x.region === code);
              const choisie = choisies.includes(code);
              return (
                <button
                  key={code}
                  type="button"
                  className={v ? `tuile seq-${classe(v.valeur, valeurs)}` : "tuile absente"}
                  style={{ gridRow: pos.ligne, gridColumn: pos.colonne }}
                  aria-pressed={choisie}
                  aria-label={
                    v
                      ? t("carte.tuile", { zone: v.zone.libelle, valeur: v.valeur_affichee, unite: r.unite })
                      : t("carte.tuileAbsente", { zone: nomRegion(code) })
                  }
                  onClick={() => onZone(code)}
                >
                  <span className="tuile-nom">{nomRegion(code)}</span>
                  <span className="tuile-valeur">{v ? chiffres(v.valeur_affichee) : "–"}</span>
                </button>
              );
            })}
          </div>
          <div className="carte-legende" aria-hidden="true">
            <span>{t("situer.carte.basse")}</span>
            {[1, 2, 3, 4, 5].map((c) => <span key={c} className={`pastille seq-${c}`} />)}
            <span>{t("situer.carte.haute")}</span>
            {r.absents.length > 0 && (
              <>
                <span className="pastille absente" />
                <span>{t("carte.sansValeur")}</span>
              </>
            )}
          </div>
        </>
      )}

      <ul className="carte-notes">
        {r.ensemble && (
          <li>
            {t("carte.ensemble", { valeur: chiffres(r.ensemble.valeur_affichee), unite: r.unite, periode: r.libelle_periode ?? "" })}
          </li>
        )}
        <li>{t("carte.unite", { unite: r.unite })}</li>
        {r.valeurs.length > 0 && r.absents.length > 0 && (
          <li>{t("carte.absents", { periode: r.libelle_periode ?? "", zones: r.absents.map(nomRegion).join(", ") })}</li>
        )}
        {academies && <li>{t("carte.academies")}</li>}
        {nonObservee && <li>{t("carte.nonObservee")}</li>}
        <li>{t("situer.carte.schema")}</li>
      </ul>

      {r.sources.length > 0 && (
        <aside className="bloc-source" aria-label={t("explorer.sources")}>
          <p className="bloc-source-titre"><Livre />{t("explorer.sources")}</p>
          {r.sources.map((src) => (
            <div key={src.url}>
              <p>{titreSource(src.titre)}</p>
              <p className="discret">{src.libelle}</p>
            </div>
          ))}
        </aside>
      )}
    </section>
  );
}
