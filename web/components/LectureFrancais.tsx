"use client";

import { useEffect, useRef, useState } from "react";
import { useLangue } from "@/i18n/langue";
import { Lecture, Pause } from "./icones";

/** Une voix française installée sur l'appareil (jamais une voix en ligne : le texte ne quitte pas l'appareil). */
function voixFrancaise(): SpeechSynthesisVoice | null {
  const voix = window.speechSynthesis.getVoices().filter((v) => v.localService && v.lang.toLowerCase().startsWith("fr"));
  return voix.find((v) => v.lang === "fr-SN") ?? voix.find((v) => v.lang === "fr-FR") ?? voix[0] ?? null;
}

/**
 * Texte prêt à être dit : les séparateurs de milliers (espaces fines) sont retirés, sinon la voix lit
 * « 2 463 677 » chiffre par chiffre ; « · » devient une pause.
 */
export function aDire(texte: string): string {
  return texte
    .replace(/(\d)[\s\u202f\u00a0](?=\d{3}\b)/g, "$1")
    .replace(/\s·\s/g, ", ");
}

/**
 * Réponse en français lue à voix haute par la voix de l'appareil (Web Speech), à côté de la voix wolof du
 * serveur (décision 0040) : rien n'est téléchargé ni envoyé. Le lecteur n'apparaît que si l'appareil a une voix
 * française locale ; la lecture s'arrête quand on quitte la page.
 */
export function LectureFrancais({ texte }: { texte: string }) {
  const { t } = useLangue();
  const [voix, setVoix] = useState<SpeechSynthesisVoice | null>(null);
  const [lecture, setLecture] = useState(false);
  const enCours = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const choisir = () => setVoix(voixFrancaise());
    choisir();
    // Les voix arrivent souvent après le premier rendu (Chrome)
    window.speechSynthesis.addEventListener("voiceschanged", choisir);
    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", choisir);
      window.speechSynthesis.cancel();
    };
  }, []);

  if (!voix) return null;

  function basculer() {
    const synthese = window.speechSynthesis;
    if (lecture) {
      synthese.cancel();
      setLecture(false);
      return;
    }
    synthese.cancel();
    const u = new SpeechSynthesisUtterance(aDire(texte));
    u.voice = voix;
    u.lang = voix?.lang ?? "fr-FR";
    u.rate = 0.95;
    u.onend = u.onerror = () => {
      if (enCours.current === u) setLecture(false);
    };
    enCours.current = u;
    synthese.speak(u);
    setLecture(true);
  }

  return (
    <div className="lecteur-audio">
      <button type="button" className="lecteur-bouton" aria-label={t(lecture ? "lecture.arreter" : "lecture.ecouter")} onClick={basculer}>
        {lecture ? <Pause taille={18} /> : <Lecture taille={18} />}
      </button>
      <span className="lecteur-texte">
        <strong>{t("audio.titre")}</strong>
        <span>{t("lecture.voix")}</span>
      </span>
    </div>
  );
}
