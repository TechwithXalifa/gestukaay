"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ChampQuestion } from "@/components/ChampQuestion";
import { Ecoute } from "@/components/Ecoute";
import { Fleche } from "@/components/icones";
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
      const r = await demander(voix ? { question: q, source: "voix", ...voix } : { question: q });
      router.push(`/r/${r.reponse.id}`);
    } catch (e) {
      setErreur(e);
    }
  }

  const horsLigne = !enLigne || (erreur instanceof ErreurApi && erreur.horsLigne);

  return (
    <div className="site">
      <Entete />
      <main className="accueil">
        <p className="eyebrow">{t("accueil.eyebrow")}</p>
        <h1 className="titre-accueil">{t("accueil.titre1")}<br />{t("accueil.titre2")}</h1>
        <p className="chapeau">{t("accueil.chapeau")}</p>
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
                <span lang={e.wo ? "wo" : undefined}>{e.texte}</span>
              </button>
            ))}
          </div>
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
