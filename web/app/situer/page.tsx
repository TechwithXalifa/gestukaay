"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { SituateRequest } from "@contracts/situate_request";
import type { SituateResponse } from "@contracts/situate_response";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { Cadenas, Chevron, Coche } from "@/components/icones";
import { ResultatSituer } from "@/components/ResultatSituer";
import { useLangue } from "@/i18n/langue";
import { situer } from "@/lib/api";
import { REGIONS } from "@/lib/regions";

type Tranche = SituateRequest["depenses_mensuelles"];
// Contrat 1.3.0 (décision 0012) : trois tranches au-delà de 500 000 ; « plus_500k » n'est plus proposée
const TRANCHES: Tranche[] = [
  "moins_50k", "50k_100k", "100k_200k", "200k_350k", "350k_500k", "500k_750k", "750k_1m", "plus_1m",
];
const TOTAL = 3;

/**
 * « Où je me situe » (EF-37 à EF-40, décision 0004 §2). Une question par
 * écran. Les réponses vivent seulement dans l'état de cette page : rien dans
 * le stockage du navigateur, rien côté serveur (US-21).
 * Le niveau d'instruction n'est pas demandé tant qu'il n'est pas exploité
 * (minimisation, contrat v1.1.1).
 */
export default function Situer() {
  const { t } = useLangue();
  const [etape, setEtape] = useState(0); // 0 intro, 1 région, 2 taille, 3 dépenses, 4 résultat
  const [region, setRegion] = useState<string | null>(null);
  const [taille, setTaille] = useState(5);
  const [depenses, setDepenses] = useState<Tranche | null>(null);
  const [resultat, setResultat] = useState<SituateResponse | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const premierAffichage = useRef(true);
  const continuer = useRef<HTMLButtonElement>(null);

  // Une option touchée ou cliquée amène « Continuer » à l'écran : sur téléphone, il était sous les
  // 14 régions. Un bouton collé en bas aurait recouvert des options (revue UI du 08/10). Pas au
  // clavier : chaque flèche ferait sortir de l'écran l'option qui a le focus (revue de la PR #155).
  function montrerContinuer() {
    const doux = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    requestAnimationFrame(() => continuer.current?.scrollIntoView({ block: "nearest", behavior: doux ? "smooth" : "auto" }));
  }

  // Chaque étape s'ouvre en haut, le focus sur sa question (WCAG 2.4.3) : la page restait défilée
  // comme à l'étape précédente, titre coupé et barre de progression hors de l'écran (revue UI).
  useEffect(() => {
    if (premierAffichage.current) {
      premierAffichage.current = false;
      return;
    }
    window.scrollTo({ top: 0 });
    const titre = document.querySelector<HTMLElement>("main#contenu h1");
    if (titre) {
      titre.tabIndex = -1;
      titre.focus({ preventScroll: true });
    }
  }, [etape, resultat, erreur]);

  async function calculer() {
    if (!region || !depenses) return;
    setEtape(4);
    setResultat(null);
    setErreur(null);
    try {
      setResultat(await situer({ region, taille_menage: taille, depenses_mensuelles: depenses }));
    } catch (e) {
      setErreur(e);
    }
  }

  function recommencer() {
    setRegion(null);
    setTaille(5);
    setDepenses(null);
    setResultat(null);
    setEtape(0);
  }

  return (
    <div className="site">
      <Entete actif="situer" />
      <main id="contenu" tabIndex={-1} className="situer">
        {etape === 0 && (
          <section className="carte">
            <h1 className="titre-situer">{t("situer.titre")}</h1>
            <p className="explication">{t("situer.intro")}</p>
            <p className="garantie"><Cadenas taille={16} />{t("situer.garantie")}</p>
            <button type="button" className="primaire large-mobile" onClick={() => setEtape(1)}>{t("situer.commencer")}</button>
          </section>
        )}

        {etape >= 1 && etape <= 3 && (
          <form
            className="questionnaire"
            onSubmit={(e) => {
              e.preventDefault();
              if (etape < 3) setEtape(etape + 1);
              else calculer();
            }}
          >
            <div className="stepper-haut">
              <button type="button" className="bouton-retour" aria-label={t("situer.retour")} onClick={() => setEtape(etape - 1)}>
                <Chevron />
              </button>
              <p>{t("situer.etape", { n: String(etape), total: String(TOTAL) })}</p>
              <span />
            </div>
            <div role="progressbar" aria-label={t("situer.progression")} aria-valuemin={0} aria-valuemax={TOTAL} aria-valuenow={etape} className="progression">
              <div style={{ width: `${(etape / TOTAL) * 100}%` }} />
            </div>

            {etape === 1 && (
              <fieldset>
                <legend><h1 className="titre-situer">{t("situer.q.region")}</h1></legend>
                <div className="options grille">
                  {REGIONS.map((r) => (
                    <label key={r.code} className={region === r.code ? "option choisie" : "option"} onPointerUp={montrerContinuer}>
                      <input type="radio" name="region" className="sr-only" checked={region === r.code} onChange={() => setRegion(r.code)} />
                      {r.libelle}
                      {region === r.code && <Coche />}
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            {etape === 2 && (
              <fieldset>
                <legend><h1 className="titre-situer">{t("situer.q.taille")}</h1></legend>
                <p className="aide">{t("situer.q.tailleAide")}</p>
                <div className="compteur">
                  <button type="button" aria-label={t("situer.moins")} onClick={() => setTaille(Math.max(1, taille - 1))} disabled={taille <= 1}>−</button>
                  <label>
                    <span className="sr-only">{t("situer.q.taille")}</span>
                    <input
                      type="number"
                      inputMode="numeric"
                      min={1}
                      max={40}
                      value={taille}
                      onChange={(e) => setTaille(Math.min(40, Math.max(1, Number(e.target.value) || 1)))}
                    />
                  </label>
                  <button type="button" aria-label={t("situer.plus")} onClick={() => setTaille(Math.min(40, taille + 1))} disabled={taille >= 40}>+</button>
                </div>
                <p className="aide centre">{taille} {t("situer.personnes")}</p>
              </fieldset>
            )}

            {etape === 3 && (
              <fieldset>
                <legend><h1 className="titre-situer">{t("situer.q.depenses")}</h1></legend>
                <p className="aide">{t("situer.q.depensesAide")}</p>
                <div className="options">
                  {TRANCHES.map((d) => (
                    <label key={d} className={depenses === d ? "option choisie" : "option"} onPointerUp={montrerContinuer}>
                      <input type="radio" name="depenses" className="sr-only" checked={depenses === d} onChange={() => setDepenses(d)} />
                      {t(`situer.d.${d}`)}
                      {depenses === d && <Coche />}
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            <p className="garantie"><Cadenas taille={16} />{t("situer.garantie")}</p>
            <button
              ref={continuer}
              type="submit"
              className="primaire continuer"
              disabled={(etape === 1 && !region) || (etape === 3 && !depenses)}
            >
              {t(etape < 3 ? "situer.continuer" : "situer.voir")}
            </button>
          </form>
        )}

        {etape === 4 &&
          (erreur ? (
            <Erreur erreur={erreur} onReessayer={calculer} />
          ) : resultat ? (
            <>
              <ResultatSituer r={resultat} />
              <div className="actions-situer">
                <button type="button" className="secondaire" onClick={recommencer}>{t("situer.recommencer")}</button>
                <Link href="/" className="primaire">{t("situer.question")}</Link>
              </div>
            </>
          ) : (
            <Chargement />
          ))}
      </main>
      <PiedDePage />
    </div>
  );
}
