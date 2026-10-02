"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { AskResponse } from "@contracts/ask_response";
import { ChampQuestion } from "@/components/ChampQuestion";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { Reponse } from "@/components/Reponse";
import { confirmer, demander, lireReponse } from "@/lib/api";

/** Page réponse : adresse stable et partageable (EF-29). */
export default function PageReponse({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [reponse, setReponse] = useState<AskResponse | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [enCours, setEnCours] = useState(true);

  const charger = useCallback(async (appel: () => Promise<AskResponse>, naviguer = false) => {
    setEnCours(true);
    setErreur(null);
    try {
      const r = await appel();
      if (naviguer) router.push(`/r/${r.reponse.id}`);
      else setReponse(r);
    } catch (e) {
      setErreur(e);
    } finally {
      setEnCours(false);
    }
  }, [router]);

  useEffect(() => {
    charger(() => lireReponse(id));
  }, [id, charger]);

  const r = reponse?.reponse;
  return (
    <div className="site">
      <Entete />
      <main className="page-reponse">
        <ChampQuestion
          key={r?.id}
          initiale={r?.question}
          enCours={enCours}
          onEnvoyer={(q) => charger(() => demander({ question: q }), true)}
        />
        {erreur ? (
          <Erreur erreur={erreur} onReessayer={() => charger(() => lireReponse(id))} />
        ) : enCours || !r ? (
          <Chargement />
        ) : (
          <Reponse
            r={r}
            onChoix={(choix) => charger(() => confirmer(r.id, choix), true)}
            onQuestion={(q) => charger(() => demander({ question: q }), true)}
          />
        )}
      </main>
      <PiedDePage adresse={r?.url} />
    </div>
  );
}
