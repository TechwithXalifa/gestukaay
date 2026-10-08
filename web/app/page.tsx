"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Fragment, useState } from "react";
import { ChampQuestion } from "@/components/ChampQuestion";
import { Compteur } from "@/components/Compteur";
import { Ecoute } from "@/components/Ecoute";
import { Bouclier, Donnees, Fleche, Livre, Micro, Question, Repere } from "@/components/icones";
import { DOMAINES_PRINCIPAUX } from "@/lib/domaines";
import { MESURE } from "@/lib/mesure";
import { SOCLE } from "@/lib/socle";
import { insecables } from "@/lib/typo";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { HorsLigne } from "@/components/HorsLigne";
import { MicroRefuse } from "@/components/MicroRefuse";
import { useEnLigne } from "@/hooks/useEnLigne";
import { useLangue } from "@/i18n/langue";
import type { AskRequest } from "@contracts/ask_request";
import { demander, ErreurApi } from "@/lib/api";

const EXEMPLES = [
  { texte: "Combien d'habitants à Thiès ?" },
  { texte: "Population de Dakar et de Thiès en 2023" },
  { texte: "Ñaata nit ñoo dëkk Tiés ?", wo: true },
  { texte: "Population de la ville de Thiès en 2023" },
];

const nombre = new Intl.NumberFormat("fr-FR");
const pourcent = new Intl.NumberFormat("fr-FR", { style: "percent", maximumFractionDigits: 1 });

/** « Recevez le chiffre *officiel*. » : le mot entre astérisques passe en or (un seul, design system). */
function avecMot(texte: string) {
  return texte.split(/\*([^*]+)\*/).map((morceau, i) => (i % 2 ? <em key={i}>{morceau}</em> : <Fragment key={i}>{morceau}</Fragment>));
}

export default function Accueil() {
  const router = useRouter();
  const enLigne = useEnLigne();
  const { t } = useLangue();
  const [question, setQuestion] = useState<string | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [ecoute, setEcoute] = useState(false);
  const [microRefuse, setMicroRefuse] = useState(false);

  async function poser(q: string, voix?: Pick<AskRequest, "transcription_brute" | "langue">) {
    setQuestion(q);
    setErreur(null);
    setEcoute(false);
    setMicroRefuse(false);
    try {
      const r = await demander(voix ? { question: q, source: "voix", audio_retour: true, ...voix } : { question: q });
      router.push(`/r/${r.reponse.id}`);
    } catch (e) {
      setErreur(e);
    }
  }

  const horsLigne = !enLigne || (erreur instanceof ErreurApi && erreur.horsLigne);
  const m = MESURE;

  return (
    <div className="site">
      <Entete />
      <main id="contenu" tabIndex={-1} className="accueil">
        <section className="heros sombre ecran">
          <div className="heros-int">
            <h1 className="titre-accueil monte monte-1">{t("accueil.titre1")}<br />{avecMot(t("accueil.titre2"))}</h1>
            <p className="chapeau monte monte-2">{t("accueil.chapeau")}</p>
            {/* 7.1 n° 2 et 8.3 : sur mobile, le micro est l'élément le plus visible de l'accueil (96 px) */}
            {!horsLigne && (
              <button type="button" className="micro-geant" onClick={() => setEcoute(true)}>
                <span className="micro-geant-rond"><Micro taille={40} /></span>
                <span>{t("accueil.parler")}</span>
              </button>
            )}
            <div className="monte monte-3" style={{ width: "100%" }}>
              <ChampQuestion
                grand
                desactive={horsLigne}
                enCours={question !== null && !erreur}
                onEnvoyer={poser}
                onMicro={() => setEcoute(true)}
              />
            </div>
            {!horsLigne && (
              <div className="exemples monte monte-4">
                {EXEMPLES.map((e) => (
                  <button key={e.texte} type="button" className="puce" onClick={() => poser(e.texte)}>
                    {e.wo && <span className="marqueur-wo">WO</span>}
                    <span lang={e.wo ? "wo" : undefined}>{insecables(e.texte)}</span>
                  </button>
                ))}
              </div>
            )}
            {!horsLigne && (
              <ul className="garanties" aria-label={t("accueil.garanties")}>
                <li><Bouclier taille={16} />{t("accueil.garantie1")}</li>
                <li><Livre taille={16} />{t("accueil.garantie2")}</li>
                <li><Donnees taille={16} />{t("accueil.garantie3")}</li>
              </ul>
            )}
          </div>
          <div className="frise defile" aria-hidden="true" />
        </section>

        {(horsLigne || microRefuse || erreur || question) && (
          <div className="section-accueil">
            <div className="section-int zone-etat">
              {horsLigne ? (
                <HorsLigne onReessayer={() => (question ? poser(question) : location.reload())} />
              ) : microRefuse ? (
                <MicroRefuse onReessayer={() => setEcoute(true)} />
              ) : erreur ? (
                <Erreur erreur={erreur} onReessayer={() => question && poser(question)} />
              ) : (
                question && <Chargement question={question} />
              )}
            </div>
          </div>
        )}

        {!horsLigne && !question && (
          <>
            <section className="section-accueil ecran" aria-labelledby="titre-socle">
              <div className="section-int apparait">
                <div className="section-tete">
                  <div>
                    <h2 id="titre-socle" className="sous-titre">{t("accueil.socle.titre")}</h2>
                  </div>
                </div>
                <ul className="stats">
                  <li><strong><Compteur texte={nombre.format(SOCLE.valeurs)} /></strong><span>{t("accueil.socle.valeurs")}</span></li>
                  <li><strong><Compteur texte={nombre.format(SOCLE.indicateurs)} /></strong><span>{t("accueil.socle.indicateurs")}</span></li>
                  <li><strong><Compteur texte={String(SOCLE.producteurs)} /></strong><span>{t("accueil.socle.producteurs")}</span></li>
                  <li><strong><Compteur texte={String(SOCLE.regions)} /></strong><span>{t("accueil.socle.zones", { departements: String(SOCLE.departements) })}</span></li>
                </ul>
              </div>
            </section>

            <section className="section-accueil alt domaines ecran" aria-labelledby="titre-domaines">
              <div className="section-int apparait">
                <div className="section-tete">
                  <div>
                    <h2 id="titre-domaines" className="sous-titre">{t("domaines.accueil")}</h2>
                  </div>
                  <Link href="/domaines" className="lien-situer">
                    {t("domaines.tous")} <Fleche taille={16} />
                  </Link>
                </div>
                <ul className="grille-domaines">
                  {DOMAINES_PRINCIPAUX.map((d) => (
                    <li key={d.nom}>
                      <button type="button" onClick={() => poser(d.exemple)}>
                        <strong>{d.nom}</strong>
                        <span>{insecables(d.exemple)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            <section className="section-accueil ecran" aria-labelledby="titre-facons">
              <div className="section-int apparait">
                <div>
                  <h2 id="titre-facons" className="sous-titre">{t("accueil.facons.titre")}</h2>
                </div>
                <ul className="facons">
                  <li>
                    <a href="#question">
                      <span className="facon-icone"><Question taille={26} /></span>
                      <strong>{t("accueil.facons.demander")}</strong>
                      <span>{t("accueil.facons.demanderTexte")}</span>
                      <em>{t("accueil.facons.demanderLien")} <Fleche taille={16} /></em>
                    </a>
                  </li>
                  <li>
                    <Link href="/explorer">
                      <span className="facon-icone"><Donnees taille={26} /></span>
                      <strong>{t("accueil.facons.explorer")}</strong>
                      <span>{t("accueil.facons.explorerTexte")}</span>
                      <em>{t("accueil.facons.explorerLien")} <Fleche taille={16} /></em>
                    </Link>
                  </li>
                  <li>
                    <Link href="/situer">
                      <span className="facon-icone"><Repere taille={26} /></span>
                      <strong>{t("accueil.facons.situer")}</strong>
                      <span>{t("accueil.facons.situerTexte")}</span>
                      <em>{t("accueil.facons.situerLien")} <Fleche taille={16} /></em>
                    </Link>
                  </li>
                </ul>
              </div>
            </section>

            <section className="section-accueil confiance sombre ecran" aria-labelledby="titre-confiance">
              <div className="section-int apparait">
                <div>
                  <h2 id="titre-confiance" className="sous-titre">{t("accueil.confiance.titre")}</h2>
                  <p className="chapeau" style={{ marginTop: 8 }}>{t("accueil.confiance.texte", { n: String(m.questions.total), date: m.date })}</p>
                </div>
                <ul className="stats">
                  <li><strong><Compteur texte={pourcent.format(m.bonne.reussies / m.bonne.sur)} /></strong><span>{t("accueil.confiance.bonne")}</span></li>
                  <li><strong><Compteur texte={pourcent.format(m.refus.reussis / m.refus.sur)} /></strong><span>{t("accueil.confiance.refus")}</span></li>
                  <li><strong>{(m.latence.medianeMs / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} s</strong><span>{t("accueil.confiance.temps")}</span></li>
                  <li><strong>{m.inventes}</strong><span>{t("accueil.confiance.invente")}</span></li>
                </ul>
                <Link href="/methode" className="lien">{t("accueil.confiance.lien")} <Fleche taille={16} /></Link>
              </div>
            </section>
          </>
        )}
      </main>
      <PiedDePage />
      {ecoute && (
        <Ecoute
          onEnvoyer={(q, brute, langue) => poser(q, { transcription_brute: brute, langue })}
          onFermer={() => setEcoute(false)}
          onRefus={() => {
            setEcoute(false);
            setMicroRefuse(true);
          }}
        />
      )}
    </div>
  );
}
