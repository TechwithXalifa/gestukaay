"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FicheIndicateur } from "@contracts/fiche_indicateur";
import type { SeriesResponse } from "@contracts/series_response";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { Copier, Externe, Fleche, Livre } from "@/components/icones";
import { Integrer } from "@/components/Integrer";
import { Suivre } from "@/components/Suivre";
import type { Cle } from "@/i18n/fr";
import { useLangue } from "@/i18n/langue";
import { demander, ErreurApi, fiche, series } from "@/lib/api";
import { chiffres, titreSource } from "@/lib/typo";

const dateLongue = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" });

/** Fiche indicateur (cahier 5.5, US-19, maquette Fiche, décision 0023). */
export default function Fiche() {
  const { t } = useLangue();
  const router = useRouter();
  const { code } = useParams<{ code: string }>();
  const [f, setF] = useState<FicheIndicateur | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);
  // Dernière valeur nationale (audit du 09/10 : la fiche ne montrait aucun chiffre). Facultative :
  // sans série nationale ou si l'appel échoue, la fiche reste complète sans elle.
  const [dernier, setDernier] = useState<{ s: SeriesResponse; i: number } | null>(null);

  const charger = () => {
    setErreur(null);
    fiche(decodeURIComponent(code)).then(setF).catch(setErreur);
  };
  useEffect(charger, [code]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (f) document.title = `${f.indicateur.libelle} · Gëstukaay`;
  }, [f]);

  useEffect(() => {
    setDernier(null);
    if (!f?.indicateur.niveaux.includes("pays")) return;
    let actif = true;
    series({ indicateur: f.indicateur.code, zones: ["SN"] })
      .then((s) => {
        // Jamais une projection future (décision 0035, comme les réponses) : l'espérance de vie donnait 2035
        const points = s.series[0]?.points ?? [];
        const an = new Date().getFullYear();
        let i = points.length - 1;
        while (i > 0 && Number(points[i].periode.slice(0, 4)) > an) i--;
        if (actif && points.length > 0) setDernier({ s, i });
      })
      .catch(() => {});
    return () => {
      actif = false;
    };
  }, [f]);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(id);
  }, [toast]);

  async function poser(libelle: string) {
    setEnvoi(true);
    try {
      const r = await demander({ question: t("fiche.question", { libelle }) });
      router.push(`/r/${r.reponse.id}`);
    } catch (e) {
      setErreur(e);
      setEnvoi(false);
    }
  }

  async function copier(texte: string) {
    try {
      await navigator.clipboard.writeText(texte);
      setToast(t("actions.citationCopiee"));
    } catch {
      setToast(t("actions.copieImpossible"));
    }
  }

  const introuvable = erreur instanceof ErreurApi && erreur.statut === 404;
  const i = f?.indicateur;
  const zonesParNiveau = f?.couverture.find((c) => c.niveau === "region")?.zones;

  return (
    <div className="site">
      <Entete actif="indicateurs" />
      <main id="contenu" tabIndex={-1} className="fiche">
        <nav aria-label="Fil d'Ariane" className="ariane">
          <Link href="/indicateurs">{t("nav.indicateurs")}</Link>
          {i && <><span aria-hidden="true">›</span><Link href={`/indicateurs?domaine=${encodeURIComponent(i.domaine)}`}>{i.domaine}</Link></>}
        </nav>

        {introuvable ? (
          <section className="carte">
            <h1 className="titre-etat">{t("fiche.introuvable")}</h1>
            <Link href="/indicateurs" className="primaire">{t("catalogue.titre")}</Link>
          </section>
        ) : erreur ? (
          <Erreur erreur={erreur} onReessayer={charger} />
        ) : !f || !i ? (
          <Chargement />
        ) : (
          <div className="fiche-corps">
            <div className="fiche-principal">
              <h1 className="titre-situer">{i.libelle}</h1>
              <p className="explication">{f.definition ?? t("fiche.sansDefinition")}</p>

              {dernier && (() => {
                const serie = dernier.s.series[0];
                const p = serie?.points[dernier.i];
                if (!serie || !p) return null;
                return (
                  <section className="fiche-derniere" aria-label={t("fiche.derniere")}>
                    <p className="fiche-derniere-titre">{t("fiche.derniere")}</p>
                    <p className="valeur">
                      <span>{chiffres(p.valeur_affichee)}</span>{" "}
                      {dernier.s.unite && <span className="unite">{dernier.s.unite}</span>}
                    </p>
                    <p className="note">
                      {serie.zone.libelle} · {p.libelle}
                      {p.nature && p.nature !== "observee" ? ` · ${t(`fiche.nature.${p.nature}` as Cle)}` : ""}
                      {" · "}{serie.source.libelle}
                    </p>
                  </section>
                );
              })()}

              <div className="fiche-actions">
                <button type="button" className="primaire" disabled={envoi} onClick={() => poser(i.libelle)}>
                  {t("fiche.poser")} <Fleche taille={16} />
                </button>
                <Link href={`/explorer?indicateur=${encodeURIComponent(i.code)}&zones=SN`} className="secondaire">
                  {t("fiche.explorer")}
                </Link>
              </div>
              <Integrer code={i.code} libelle={i.libelle} niveaux={i.niveaux} />
              <Suivre code={i.code} niveaux={i.niveaux} />

              {(f.methode || f.note_perimetre) && (
                <section>
                  <h2 className="sous-titre">{t("fiche.savoir")}</h2>
                  {f.methode && <p>{f.methode}</p>}
                  {f.note_perimetre && <p>{f.note_perimetre}</p>}
                </section>
              )}

              <section>
                <h2 className="sous-titre">{t("fiche.series")}</h2>
                <div className="tableau-defile" role="region" aria-label={t("fiche.series")} tabIndex={0}>
                  <table className="tableau">
                    <thead>
                      <tr>
                        <th scope="col">{t("fiche.niveau")}</th>
                        <th scope="col" className="nombre">{t("fiche.zones")}</th>
                        <th scope="col">{t("fiche.annees")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {f.couverture.map((c) => (
                        <tr key={c.niveau}>
                          <th scope="row">{t(`niveau.${c.niveau}` as Cle)}</th>
                          <td className="nombre">{c.zones}</td>
                          <td>{c.periodes.join(", ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {f.desagregations.length > 0 && (
                  <p className="note">{t("fiche.desagregations", { liste: f.desagregations.join(", ") })}</p>
                )}
              </section>

              <section>
                <h2 className="sous-titre">{t("fiche.citer")}</h2>
                <p className="fiche-citation">{f.citation}</p>
                <button type="button" className="secondaire" onClick={() => copier(f.citation)}>
                  <Copier />{t("actions.citer")}
                </button>
                <p role="status" aria-live="polite" className={toast ? "toast visible" : "toast"}>{toast}</p>
              </section>
            </div>

            <aside className="bloc-source fiche-bref" aria-label={t("fiche.enBref")}>
              <p className="bloc-source-titre"><Livre />{t("fiche.enBref")}</p>
              <dl>
                <dt>{t("fiche.source")}</dt>
                <dd>
                  {f.source.libelle}
                  {/* Le titre ne revient que s'il apporte quelque chose (souvent déjà dans le libellé) */}
                  {!f.source.libelle.includes(f.source.titre) && <><br /><span className="discret">{titreSource(f.source.titre)}</span></>}
                </dd>
                <dt>{t("fiche.unite")}</dt><dd>{i.unite || "–"}</dd>
                <dt>{t("fiche.periode")}</dt><dd>{i.periode_debut === i.periode_fin ? i.periode_fin : `${i.periode_debut} à ${i.periode_fin}`}</dd>
                <dt>{t("fiche.couverture")}</dt>
                <dd>{i.niveaux.map((n) => (n === "region" && zonesParNiveau ? t("fiche.regions", { n: String(zonesParNiveau) }) : t(`niveau.${n}` as Cle))).join(" · ")}</dd>
                <dt>{t("fiche.miseAJour")}</dt><dd>{dateLongue.format(new Date(f.source.date_publication))}</dd>
                <dt>{t("fiche.licence")}</dt><dd>{f.source.licence || t("fiche.licenceInconnue")}</dd>
              </dl>
              {f.source.url && (
                <a href={f.source.url} target="_blank" rel="noreferrer" className="lien">
                  {t("reponse.publication")} <Externe taille={16} />
                </a>
              )}
              {f.indicateurs_lies.length > 0 && (
                <>
                  <p className="bloc-source-titre">{t("fiche.lies")}</p>
                  <ul className="fiche-lies">
                    {f.indicateurs_lies.map((l) => (
                      <li key={l.code}><Link href={`/indicateurs/${encodeURIComponent(l.code)}`}>{l.libelle}</Link></li>
                    ))}
                  </ul>
                </>
              )}
            </aside>
          </div>
        )}
      </main>
      <PiedDePage />
    </div>
  );
}
