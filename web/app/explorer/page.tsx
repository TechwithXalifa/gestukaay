"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import type { CatalogueResponse } from "@contracts/catalogue_response";
import type { FicheIndicateur } from "@contracts/fiche_indicateur";
import type { SeriesResponse } from "@contracts/series_response";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { Graphique } from "@/components/Graphique";
import { Croix, Externe, Livre, Telecharger } from "@/components/icones";
import { useLangue } from "@/i18n/langue";
import { catalogue, fiche, series, seriesCsvUrl } from "@/lib/api";
import { REGIONS } from "@/lib/regions";

const ZONES_MAX = 6; // US-18
const ZONES = [{ code: "SN", libelle: "Sénégal" }, ...REGIONS];
const libelleZone = (code: string) => ZONES.find((z) => z.code === code)?.libelle ?? code;

/**
 * Explorer et comparer (cahier 5.5, US-18, maquette Explorer, décision 0023). Tout l'état est dans
 * l'adresse (EF-29) : indicateur, zones, période et affichage ; une vue se partage telle quelle.
 * Les zones et périodes sans donnée publiée sont signalées, jamais interpolées.
 */
export default function Page() {
  return (
    <Suspense>
      <Explorer />
    </Suspense>
  );
}

function Explorer() {
  const { t } = useLangue();
  const router = useRouter();
  const params = useSearchParams();
  const indicateur = params.get("indicateur") ?? "";
  const zones = useMemo(
    () => [...new Set((params.get("zones") ?? "SN").split(",").filter(Boolean))].slice(0, ZONES_MAX),
    [params],
  );
  const debut = params.get("debut") ?? "";
  const fin = params.get("fin") ?? "";
  const vue = params.get("vue") === "tableau" ? "tableau" : "graphique";

  const [f, setF] = useState<FicheIndicateur | null>(null);
  const [s, setS] = useState<SeriesResponse | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [essai, setEssai] = useState(0);

  function changer(nouveau: Record<string, string>) {
    const p = new URLSearchParams({ indicateur, zones: zones.join(","), debut, fin, vue, ...nouveau });
    for (const [k, v] of [...p.entries()]) if (!v || (k === "vue" && v === "graphique")) p.delete(k);
    router.replace(`/explorer?${p}`, { scroll: false });
  }

  useEffect(() => {
    if (!indicateur) return;
    let annule = false;
    setErreur(null);
    fiche(indicateur).then((r) => !annule && setF(r)).catch((e) => !annule && setErreur(e));
    return () => {
      annule = true;
    };
  }, [indicateur, essai]);

  useEffect(() => {
    if (!indicateur || zones.length === 0) return;
    let annule = false;
    setErreur(null);
    series({ indicateur, zones, debut, fin })
      .then((r) => !annule && setS(r))
      .catch((e) => !annule && setErreur(e));
    return () => {
      annule = true;
    };
  }, [indicateur, zones, debut, fin, essai]);

  const periodes = useMemo(
    () => [...new Set(f?.couverture.flatMap((c) => c.periodes) ?? [])].sort(),
    [f],
  );
  const regionsPubliees = f?.indicateur.niveaux.includes("region") ?? true;
  const ajoutables = ZONES.filter((z) => !zones.includes(z.code) && (z.code === "SN" || regionsPubliees));
  const lignes = useMemo(() => [...new Set(s?.series.flatMap((x) => x.points.map((p) => p.periode)) ?? [])].sort(), [s]);
  const sources = s ? [...new Map(s.series.map((x) => [x.source.url, x.source])).values()] : [];

  return (
    <div className="site">
      <Entete actif="explorer" />
      <main id="contenu" tabIndex={-1} className="explorer">
        <p className="eyebrow">{t("explorer.eyebrow")}</p>
        <h1 className="titre-situer">{f?.indicateur.libelle ?? t("explorer.titre")}</h1>

        {!indicateur ? (
          <Choisir onChoix={(code) => changer({ indicateur: code, debut: "", fin: "" })} />
        ) : erreur ? (
          <Erreur erreur={erreur} onReessayer={() => setEssai((n) => n + 1)} />
        ) : (
          <div className="explorer-corps">
            <form className="explorer-filtres carte" aria-label={t("explorer.eyebrow")} onSubmit={(e) => e.preventDefault()}>
              <fieldset>
                <legend>{t("explorer.indicateur")}</legend>
                <p className="explorer-indicateur">{f?.indicateur.libelle ?? "…"}</p>
                <button type="button" className="lien-bouton" onClick={() => changer({ indicateur: "", debut: "", fin: "" })}>
                  {t("explorer.changer")}
                </button>
              </fieldset>

              <fieldset>
                <legend>{t("explorer.zones")}</legend>
                <ul className="explorer-zones">
                  {zones.map((z) => (
                    <li key={z}>
                      <span>{libelleZone(z)}</span>
                      {zones.length > 1 && (
                        <button
                          type="button"
                          className="bouton-retirer"
                          aria-label={t("explorer.retirer", { zone: libelleZone(z) })}
                          onClick={() => changer({ zones: zones.filter((x) => x !== z).join(",") })}
                        >
                          <Croix taille={16} />
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                {zones.length < ZONES_MAX && ajoutables.length > 0 && (
                  <div className="explorer-champ">
                    <label htmlFor="explorer-ajouter">{t("explorer.ajouter")}</label>
                    <select id="explorer-ajouter" value="" onChange={(e) => e.target.value && changer({ zones: [...zones, e.target.value].join(",") })}>
                      <option value="">…</option>
                      {ajoutables.map((z) => <option key={z.code} value={z.code}>{z.libelle}</option>)}
                    </select>
                  </div>
                )}
                <p className="note">{t("explorer.compte", { n: String(zones.length) })}</p>
              </fieldset>

              <fieldset>
                <legend>{t("explorer.periode")}</legend>
                <div className="explorer-periode">
                  <div className="explorer-champ">
                    <label htmlFor="explorer-debut">{t("explorer.debut")}</label>
                    <select id="explorer-debut" value={debut} onChange={(e) => changer({ debut: e.target.value })}>
                      <option value="">{t("explorer.toutes")}</option>
                      {periodes.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div className="explorer-champ">
                    <label htmlFor="explorer-fin">{t("explorer.fin")}</label>
                    <select id="explorer-fin" value={fin} onChange={(e) => changer({ fin: e.target.value })}>
                      <option value="">{t("explorer.toutes")}</option>
                      {periodes.filter((p) => !debut || p >= debut).map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                </div>
              </fieldset>

              <fieldset>
                <legend>{t("explorer.affichage")}</legend>
                <div role="group" aria-label={t("explorer.affichage")} className="bascule">
                  {(["graphique", "tableau"] as const).map((v) => (
                    <button key={v} type="button" aria-pressed={vue === v} onClick={() => changer({ vue: v })}>
                      {t(`explorer.${v}`)}
                    </button>
                  ))}
                </div>
              </fieldset>
              <p className="note">{t("explorer.nonInterpole")}</p>
            </form>

            <section className="explorer-resultat carte" aria-live="polite">
              {!s ? (
                <Chargement />
              ) : (
                <>
                  <div className="explorer-entete">
                    <p className="eyebrow">{f?.indicateur.domaine}</p>
                    <a className="secondaire" href={seriesCsvUrl({ indicateur, zones, debut, fin })} download>
                      <Telecharger />{t("explorer.csv")}
                    </a>
                  </div>
                  {s.absents.length > 0 && (
                    <p className="bandeau-discret" role="status">
                      {t("explorer.absents", { zones: s.absents.map(libelleZone).join(", ") })}
                    </p>
                  )}
                  {s.series.length === 0 ? (
                    <p className="explication">{t("explorer.aucune")}</p>
                  ) : vue === "graphique" && s.graphique ? (
                    <Graphique g={s.graphique} />
                  ) : (
                    <div className="tableau-defile" role="region" aria-label={s.indicateur.libelle} tabIndex={0}>
                      <table className="tableau">
                        <thead>
                          <tr>
                            <th scope="col">{t("explorer.zone")}</th>
                            {lignes.map((p) => <th key={p} scope="col" className="nombre">{p}</th>)}
                          </tr>
                        </thead>
                        <tbody>
                          {s.series.map((x) => (
                            <tr key={x.zone.code}>
                              <th scope="row">{x.zone.libelle}</th>
                              {lignes.map((p) => (
                                <td key={p} className="nombre">{x.points.find((pt) => pt.periode === p)?.valeur_affichee ?? "–"}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p className="note">{s.unite}</p>
                    </div>
                  )}

                  <aside className="bloc-source" aria-label={t("explorer.sources")}>
                    <p className="bloc-source-titre"><Livre />{t("explorer.sources")}</p>
                    {sources.map((src) => (
                      <div key={src.url}>
                        <p>{src.titre}</p>
                        <p className="discret">{src.libelle}</p>
                      </div>
                    ))}
                    <Link href={`/indicateurs/${encodeURIComponent(indicateur)}`} className="lien">
                      {t("explorer.fiche")} <Externe taille={16} />
                    </Link>
                  </aside>
                  <p className="note">{t("explorer.lien")}</p>
                </>
              )}
            </section>
          </div>
        )}
      </main>
      <PiedDePage />
    </div>
  );
}

/** Sans indicateur dans l'adresse : recherche dans le catalogue. */
function Choisir({ onChoix }: { onChoix: (code: string) => void }) {
  const { t } = useLangue();
  const [q, setQ] = useState("");
  const [r, setR] = useState<CatalogueResponse | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);

  function chercher(texte: string) {
    setErreur(null);
    catalogue({ q: texte, limite: 10 }).then(setR).catch(setErreur);
  }
  useEffect(() => chercher(""), []);

  return (
    <section className="carte explorer-choisir">
      <p className="explication">{t("explorer.choisir")}</p>
      <form
        role="search"
        className="catalogue-filtres"
        onSubmit={(e) => {
          e.preventDefault();
          chercher(q.trim());
        }}
      >
        <label htmlFor="explorer-recherche" className="sr-only">{t("catalogue.recherche")}</label>
        <input id="explorer-recherche" type="search" value={q} onChange={(e) => setQ(e.target.value)}
               placeholder={t("catalogue.recherche")} maxLength={100} />
        <button type="submit" className="primaire">{t("catalogue.rechercher")}</button>
      </form>
      {erreur ? (
        <Erreur erreur={erreur} onReessayer={() => chercher(q)} />
      ) : (
        <ul className="catalogue-liste">
          {r?.indicateurs.map((i) => (
            <li key={i.code}>
              <button type="button" onClick={() => onChoix(i.code)}>
                <strong>{i.libelle}</strong>
                <span className="discret">{i.producteur} · {i.operation} · {i.periode_debut} à {i.periode_fin}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
