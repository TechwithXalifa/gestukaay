"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { AskResponse } from "@contracts/ask_response";
import { ChampQuestion } from "@/components/ChampQuestion";
import { Ecoute } from "@/components/Ecoute";
import { Entete, PiedDePage } from "@/components/Entete";
import { Chargement, Erreur } from "@/components/Etats";
import { HorsLigne } from "@/components/HorsLigne";
import { MicroRefuse } from "@/components/MicroRefuse";
import { Reponse } from "@/components/Reponse";
import { useEnLigne } from "@/hooks/useEnLigne";
import { useLangue } from "@/i18n/langue";
import { confirmer, demander, ErreurApi, lireReponse } from "@/lib/api";
import { memoriser, retrouver } from "@/lib/historique";

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
  const [ecoute, setEcoute] = useState(false);

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

  // Titre de l'onglet = la question (WCAG 2.4.2), annoncé par Next au changement de page
  useEffect(() => {
    if (r?.question) document.title = `${r.question} · Gëstukaay`;
  }, [r?.question]);

  return (
    <div className="site">
      <Entete />
      <main id="contenu" tabIndex={-1} className="page-reponse">
        <ChampQuestion
          key={r?.id}
          initiale={r?.question}
          enCours={enCours}
          desactive={horsLigne}
          onEnvoyer={(q) => charger(() => demander({ question: q }), true)}
          onMicro={() => setEcoute(true)}
        />
        {microRefuse && <MicroRefuse onReessayer={() => setEcoute(true)} />}
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
      {ecoute && (
        <Ecoute
          onEnvoyer={(q, brute, langue) => {
            setEcoute(false);
            charger(() => demander({ question: q, source: "voix", audio_retour: true, transcription_brute: brute, langue }), true);
          }}
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
