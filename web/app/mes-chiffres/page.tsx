"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { ReponseExacte } from "@contracts/ask_response";
import { Entete, PiedDePage } from "@/components/Entete";
import { Croix, Telecharger } from "@/components/icones";
import type { Cle } from "@/i18n/fr";
import { useLangue } from "@/i18n/langue";
import { EVENEMENT, type Favori, favoris, retirer, versCsv } from "@/lib/favoris";
import { type Consultation, effacerHistorique, historique, oublier } from "@/lib/historique";
import { chiffres, insecables } from "@/lib/typo";

function quand(iso: string, t: (c: Cle, v?: Record<string, string>) => string): string {
  const d = new Date(iso);
  const jours = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (jours === 0) return t("mesChiffres.aHeure", { heure: d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) });
  return jours === 1 ? t("mesChiffres.hier") : t("mesChiffres.le", { date: d.toLocaleDateString("fr-FR") });
}

/** Le chiffre d'une réponse exacte : la zone demandée d'un classement, sinon la première valeur. */
const principal = (r: ReponseExacte) => r.resultats.find((v) => v.mise_en_evidence) ?? r.resultats[0];

/**
 * « Mes chiffres » : les réponses épinglées et les dernières consultées, gardées sur cet appareil seulement.
 * Rien n'est envoyé ni enregistré ailleurs ; lisible hors ligne. Les chiffres épinglés se téléchargent en tableur.
 */
export default function MesChiffres() {
  const { t } = useLangue();
  const [epingles, setEpingles] = useState<Favori[]>([]);
  const [recentes, setRecentes] = useState<Consultation[]>([]);
  const [confirmer, setConfirmer] = useState(false);

  useEffect(() => {
    const lire = () => {
      setEpingles(favoris());
      setRecentes(historique());
    };
    lire();
    window.addEventListener(EVENEMENT, lire);
    return () => window.removeEventListener(EVENEMENT, lire);
  }, []);

  function telecharger() {
    const lien = document.createElement("a");
    lien.href = URL.createObjectURL(new Blob([versCsv(epingles)], { type: "text/csv;charset=utf-8" }));
    lien.download = "gestukaay-mes-chiffres.csv";
    lien.click();
    URL.revokeObjectURL(lien.href);
  }

  return (
    <div className="site">
      <Entete actif={null} />
      <main id="contenu" tabIndex={-1} className="mes-chiffres">
        <h1 className="titre-situer">{t("mesChiffres.titre")}</h1>
        <p className="chapeau">{t("mesChiffres.intro")}</p>

        <section aria-labelledby="titre-epingles">
          <div className="section-tete">
            <h2 id="titre-epingles" className="sous-titre">{t("mesChiffres.epingles", { n: String(epingles.length) })}</h2>
            {epingles.length > 0 && (
              <button type="button" className="secondaire petit" onClick={telecharger}>
                <Telecharger />{t("mesChiffres.csv")}
              </button>
            )}
          </div>
          {epingles.length === 0 ? (
            <p className="aide">{t("mesChiffres.aucunEpingle")}</p>
          ) : (
            <ul className="recentes mes-chiffres-liste">
              {epingles.map(({ r, epingleLe }) => {
                const v = principal(r);
                return (
                  <li key={r.id}>
                    <Link href={`/r/${r.id}`}>
                      <span className="discret">{insecables(r.question)}</span>
                      <span className="valeur-petite">{chiffres(v.valeur_affichee)} <span>{v.unite}</span></span>
                      <span className="discret">{v.indicateur.libelle} · {v.zone.libelle} · {v.periode.libelle}</span>
                      <span className="discret">{v.source.libelle} · {t("mesChiffres.epingleLe", { quand: quand(epingleLe, t) })}</span>
                    </Link>
                    <button type="button" className="bouton-retirer" aria-label={t("mesChiffres.retirer", { question: r.question })} onClick={() => retirer(r.id)}>
                      <Croix taille={16} />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section aria-labelledby="titre-recentes">
          <div className="section-tete">
            <h2 id="titre-recentes" className="sous-titre">{t("mesChiffres.recentes")}</h2>
            {recentes.length > 0 &&
              (confirmer ? (
                <span className="mes-chiffres-confirmer" role="group" aria-label={t("mesChiffres.effacer")}>
                  <button
                    type="button"
                    className="secondaire petit"
                    onClick={() => {
                      effacerHistorique();
                      setRecentes([]);
                      setConfirmer(false);
                    }}
                  >
                    {t("mesChiffres.confirmer")}
                  </button>
                  <button type="button" className="tertiaire petit" onClick={() => setConfirmer(false)}>{t("retour.annuler")}</button>
                </span>
              ) : (
                <button type="button" className="tertiaire petit" onClick={() => setConfirmer(true)}>{t("mesChiffres.effacer")}</button>
              ))}
          </div>
          {recentes.length === 0 ? (
            <p className="aide">{t("mesChiffres.aucuneRecente")}</p>
          ) : (
            <ul className="recentes mes-chiffres-liste">
              {recentes.map(({ reponse, consulteeLe }) => {
                const r = reponse.reponse;
                const v = r.issue === "exacte" ? principal(r) : null;
                return (
                  <li key={r.id}>
                    <Link href={`/r/${r.id}`}>
                      <span className="discret">{insecables(r.question)}</span>
                      {v && <span className="valeur-petite">{chiffres(v.valeur_affichee)} <span>{v.unite}</span></span>}
                      <span className="discret">{quand(consulteeLe, t)}</span>
                    </Link>
                    <button
                      type="button"
                      className="bouton-retirer"
                      aria-label={t("mesChiffres.oublier", { question: r.question })}
                      onClick={() => {
                        oublier(r.id);
                        setRecentes(historique());
                      }}
                    >
                      <Croix taille={16} />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
        <p className="note">{t("mesChiffres.confidentialite")}</p>
      </main>
      <PiedDePage />
    </div>
  );
}
