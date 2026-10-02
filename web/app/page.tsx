"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ChampQuestion } from "@/components/ChampQuestion";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { HorsLigne } from "@/components/HorsLigne";
import { MicroRefuse } from "@/components/MicroRefuse";
import { useEnLigne } from "@/hooks/useEnLigne";
import { useLangue } from "@/i18n/langue";
import { demander, ErreurApi } from "@/lib/api";
import { type AccesMicro, demanderMicro } from "@/lib/micro";

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
  const [micro, setMicro] = useState<AccesMicro | null>(null);

  async function poser(q: string) {
    setQuestion(q);
    setErreur(null);
    setMicro(null);
    try {
      const r = await demander({ question: q });
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
          onMicro={async () => setMicro(await demanderMicro())}
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
        <div className="zone-etat">
          {horsLigne ? (
            <HorsLigne onReessayer={() => (question ? poser(question) : location.reload())} />
          ) : micro === "refuse" ? (
            <MicroRefuse onReessayer={async () => setMicro(await demanderMicro())} />
          ) : micro ? (
            <p className="note" role="status">
              {t(micro === "accorde" ? "accueil.micro.accorde" : "accueil.micro.indisponible")}
            </p>
          ) : erreur ? (
            <Erreur erreur={erreur} onReessayer={() => question && poser(question)} />
          ) : (
            question && <Chargement question={question} />
          )}
        </div>
      </main>
      <PiedDePage />
    </div>
  );
}
