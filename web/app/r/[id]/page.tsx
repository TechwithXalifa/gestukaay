"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { AskResponse } from "@contracts/ask_response";
import { ChampQuestion } from "@/components/ChampQuestion";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { HorsLigne } from "@/components/HorsLigne";
import { MicroRefuse } from "@/components/MicroRefuse";
import { Reponse } from "@/components/Reponse";
import { useEnLigne } from "@/hooks/useEnLigne";
import { useLangue } from "@/i18n/langue";
import { confirmer, demander, ErreurApi, lireReponse } from "@/lib/api";
import { memoriser, retrouver } from "@/lib/historique";
import { demanderMicro } from "@/lib/micro";

/** Page réponse : adresse stable et partageable (EF-29), lisible hors ligne si déjà consultée (7.3). */
export default function PageReponse({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const enLigne = useEnLigne();
  const { t } = useLangue();
  const [reponse, setReponse] = useState<AskResponse | null>(null);
  const [depuisAppareil, setDepuisAppareil] = useState(false);
  const [erreur, setErreur] = useState<unknown>(null);
  const [enCours, setEnCours] = useState(true);
  const [microRefuse, setMicroRefuse] = useState(false);

  const charger = useCallback(async (appel: () => Promise<AskResponse>, naviguer = false) => {
    setEnCours(true);
    setErreur(null);
    try {
      const r = await appel();
      if (naviguer) router.push(`/r/${r.reponse.id}`);
      else {
        memoriser(r);
        setReponse(r);
        setDepuisAppareil(false);
      }
    } catch (e) {
      setErreur(e);
    } finally {
      setEnCours(false);
    }
  }, [router]);

  useEffect(() => {
    const garde = retrouver(id);
    if (garde) setReponse(garde); // affichage immédiat, rafraîchi par le réseau
    charger(() => lireReponse(id));
  }, [id, charger]);

  // Réseau indisponible mais réponse déjà consultée : on l'affiche depuis l'appareil
  useEffect(() => {
    if (erreur && retrouver(id)) setDepuisAppareil(true);
  }, [erreur, id]);

  const r = reponse?.reponse;
  const horsLigne = !enLigne || (erreur instanceof ErreurApi && erreur.horsLigne);
  const lisible = r && (!erreur || depuisAppareil);

  async function micro() {
    setMicroRefuse((await demanderMicro()) === "refuse");
  }

  return (
    <div className="site">
      <Entete />
      <main className="page-reponse">
        <ChampQuestion
          key={r?.id}
          initiale={r?.question}
          enCours={enCours}
          desactive={horsLigne}
          onEnvoyer={(q) => charger(() => demander({ question: q }), true)}
          onMicro={micro}
        />
        {microRefuse && <MicroRefuse onReessayer={micro} />}
        {horsLigne && lisible && (
          <p className="bandeau-discret" role="status">{t("reponse.horsligne")}</p>
        )}
        {lisible ? (
          <Reponse
            r={r}
            onChoix={(choix) => charger(() => confirmer(r.id, choix), true)}
            onQuestion={(q) => charger(() => demander({ question: q }), true)}
          />
        ) : horsLigne ? (
          <HorsLigne onReessayer={() => charger(() => lireReponse(id))} />
        ) : erreur ? (
          <Erreur erreur={erreur} onReessayer={() => charger(() => lireReponse(id))} />
        ) : (
          enCours && <Chargement />
        )}
      </main>
      <PiedDePage adresse={r?.url} />
    </div>
  );
}
