"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ChampQuestion } from "@/components/ChampQuestion";
import { Ecoute } from "@/components/Ecoute";
import { Coche, Fleche, Livre, Micro, Telecharger } from "@/components/icones";
import { DOMAINES_PRINCIPAUX } from "@/lib/domaines";
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

  return (
    <div className="site">
      <Entete />
      <main id="contenu" tabIndex={-1} className="accueil">
        <p className="eyebrow">{t("accueil.eyebrow")}</p>
        <h1 className="titre-accueil">{t("accueil.titre1")}<br />{t("accueil.titre2")}</h1>
        <p className="chapeau">{t("accueil.chapeau")}</p>
        {/* 7.1 n° 2 et 8.3 : sur mobile, le micro est l'élément le plus visible de l'accueil (96 px) */}
        {!horsLigne && (
          <button type="button" className="micro-geant" onClick={() => setEcoute(true)}>
            <span className="micro-geant-rond"><Micro taille={40} /></span>
            <span>{t("accueil.parler")}</span>
          </button>
        )}
        <ChampQuestion
          grand
          desactive={horsLigne}
          enCours={question !== null && !erreur}
          onEnvoyer={poser}
          onMicro={() => setEcoute(true)}
        />
        {!horsLigne && (
          <div className="exemples">
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
            <li><Coche taille={16} />{t("accueil.garantie1")}</li>
            <li><Livre taille={16} />{t("accueil.garantie2")}</li>
            <li><Telecharger taille={16} />{t("accueil.garantie3")}</li>
          </ul>
        )}
        {!horsLigne && (
          <Link href="/situer" className="lien-situer">
            {t("accueil.situer")} <Fleche taille={16} />
          </Link>
        )}
        <div className="zone-etat">
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
        {!horsLigne && !question && (
          <section className="domaines" aria-labelledby="titre-domaines">
            <h2 id="titre-domaines" className="sous-titre">{t("domaines.accueil")}</h2>
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
            <Link href="/domaines" className="lien-situer">
              {t("domaines.tous")} <Fleche taille={16} />
            </Link>
          </section>
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
