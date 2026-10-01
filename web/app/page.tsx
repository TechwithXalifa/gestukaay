"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ChampQuestion } from "@/components/ChampQuestion";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { demander } from "@/lib/api";

const EXEMPLES = [
  { texte: "Combien d'habitants à Thiès ?" },
  { texte: "Population de Dakar et de Thiès en 2023" },
  { texte: "Ñaata nit ñoo dëkk Tiés ?", wo: true },
  { texte: "Population de la ville de Thiès en 2023" },
];

export default function Accueil() {
  const router = useRouter();
  const [question, setQuestion] = useState<string | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);

  async function poser(q: string) {
    setQuestion(q);
    setErreur(null);
    try {
      const r = await demander({ question: q });
      router.push(`/r/${r.reponse.id}`);
    } catch (e) {
      setErreur(e);
    }
  }

  return (
    <div className="site">
      <Entete />
      <main className="accueil">
        <p className="eyebrow">Données officielles du Sénégal</p>
        <h1 className="titre-accueil">Posez votre question.<br />Recevez le chiffre officiel.</h1>
        <p className="chapeau">En français ou en wolof. Toujours avec la source et la date.</p>
        <ChampQuestion grand enCours={question !== null && !erreur} onEnvoyer={poser} />
        <div className="exemples">
          {EXEMPLES.map((e) => (
            <button key={e.texte} type="button" className="puce" onClick={() => poser(e.texte)}>
              {e.wo && <span className="marqueur-wo">WO</span>}
              <span lang={e.wo ? "wo" : undefined}>{e.texte}</span>
            </button>
          ))}
        </div>
        <div className="zone-etat">
          {erreur ? (
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
