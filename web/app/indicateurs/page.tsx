"use client";

import { OngletsDonnees } from "@/components/OngletsDonnees";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import type { CatalogueResponse } from "@contracts/catalogue_response";
import { Entete, PiedDePage } from "@/components/Entete";
import { Erreur } from "@/components/Etats";
import { Coche, Fleche } from "@/components/icones";
import type { Cle } from "@/i18n/fr";
import { useLangue } from "@/i18n/langue";
import { catalogue } from "@/lib/api";
import { TOUS_LES_DOMAINES } from "@/lib/domaines";

const PAR_PAGE = 20;
type Indicateur = CatalogueResponse["indicateurs"][number];

/**
 * Catalogue des indicateurs (cahier 5.5, maquette Catalogue, décision 0023). La recherche et le
 * domaine sont dans l'adresse : une vue filtrée se partage telle quelle (EF-29).
 */
export default function Page() {
  return (
    <Suspense>
      <Catalogue />
    </Suspense>
  );
}

function Catalogue() {
  const { t } = useLangue();
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const domaine = params.get("domaine") ?? "";
  const [saisie, setSaisie] = useState(q);
  const [liste, setListe] = useState<Indicateur[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => setSaisie(q), [q]);

  useEffect(() => {
    let annule = false;
    setEnCours(true);
    setErreur(null);
    catalogue({ q, domaine, limite: PAR_PAGE })
      .then((r) => {
        if (annule) return;
        setListe(r.indicateurs);
        setTotal(r.total);
      })
      .catch((e) => !annule && setErreur(e))
      .finally(() => !annule && setEnCours(false));
    return () => {
      annule = true;
    };
  }, [q, domaine]);

  function filtrer(nouveau: { q?: string; domaine?: string }) {
    const p = new URLSearchParams({ q, domaine, ...nouveau });
    for (const [k, v] of [...p.entries()]) if (!v) p.delete(k);
    router.replace(`/indicateurs${p.size ? `?${p}` : ""}`, { scroll: false });
  }

  async function plus() {
    setEnCours(true);
    try {
      const r = await catalogue({ q, domaine, limite: PAR_PAGE, decalage: liste.length });
      setListe((l) => [...l, ...r.indicateurs]);
    } catch (e) {
      setErreur(e);
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="site">
      <Entete actif="indicateurs" />
      <main id="contenu" tabIndex={-1} className="catalogue">
        <OngletsDonnees actif="indicateurs" />
        <h1 className="titre-situer">{t("catalogue.titre")}</h1>
        {total !== null && !q && !domaine && (
          <p className="explication">{t("catalogue.intro", { n: total.toLocaleString("fr-FR") })}</p>
        )}

        <form
          className="catalogue-filtres"
          role="search"
          onSubmit={(e) => {
            e.preventDefault();
            filtrer({ q: saisie.trim() });
          }}
        >
          <label htmlFor="recherche-indicateur" className="sr-only">{t("catalogue.recherche")}</label>
          <input
            id="recherche-indicateur"
            type="search"
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            placeholder={t("catalogue.recherche")}
            maxLength={100}
          />
          <button type="submit" className="primaire">{t("catalogue.rechercher")}</button>
          <label className="catalogue-domaine">
            <span>{t("catalogue.domaine")}</span>
            <select value={domaine} onChange={(e) => filtrer({ domaine: e.target.value })}>
              <option value="">{t("catalogue.tous")}</option>
              {TOUS_LES_DOMAINES.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        </form>

        {erreur ? (
          <Erreur erreur={erreur} onReessayer={() => filtrer({})} />
        ) : (
          <>
            {total !== null && (q || domaine) && (
              <p className="note" role="status">{t("catalogue.resultats", { n: total.toLocaleString("fr-FR") })}</p>
            )}
            {total === 0 && <p className="explication">{t("catalogue.aucun")}</p>}
            <ul className="catalogue-liste" aria-busy={enCours}>
              {liste.map((i) => (
                <li key={i.code}>
                  <Link href={`/indicateurs/${encodeURIComponent(i.code)}`}>
                    <span className="catalogue-tete">
                      <strong>{i.libelle}</strong>
                      {i.verifie && <span className="badge exacte"><Coche taille={14} />{t("catalogue.verifie")}</span>}
                    </span>
                    <span className="discret">
                      {i.producteur} · {i.operation} · {i.periode_debut === i.periode_fin ? i.periode_fin : `${i.periode_debut} à ${i.periode_fin}`}
                    </span>
                    <span className="discret">
                      {i.domaine} · {i.niveaux.map((n) => t(`niveau.${n}` as Cle)).join(" · ") || t("niveau.pays")}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
            {total !== null && liste.length < total && (
              <button type="button" className="secondaire" onClick={plus} disabled={enCours}>{t("catalogue.plus")}</button>
            )}
          </>
        )}

        <aside className="carte catalogue-question">
          <h2 className="sous-titre">{t("catalogue.introuvable")}</h2>
          <p className="explication">{t("catalogue.introuvableAide")}</p>
          <Link href="/" className="primaire">{t("nav.poser")} <Fleche taille={16} /></Link>
        </aside>
      </main>
      <PiedDePage />
    </div>
  );
}
