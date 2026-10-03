"use client";

import { useEffect, useRef, useState } from "react";
import { useLangue } from "@/i18n/langue";

/**
 * Réponse lue à voix haute (EF-16, maquette M-Reponse). Seules les métadonnées sont chargées
 * d'avance (durée) : sur un petit forfait, l'audio n'est téléchargé qu'au clic. Si l'audio est
 * introuvable, le lecteur disparaît : le texte reste la réponse.
 */
export function LecteurAudio({ url, langue }: { url: string; langue: string }) {
  const { t } = useLangue();
  const audio = useRef<HTMLAudioElement>(null);
  const [etat, setEtat] = useState<"pret" | "lecture" | "absent">("pret");
  const [duree, setDuree] = useState<number | null>(null);
  const [ecoule, setEcoule] = useState(0);

  useEffect(() => setEtat("pret"), [url]);
  if (etat === "absent") return null;

  const enWolof = langue === "wo";
  const secondes = Math.round(duree ?? 0);
  const minuteur = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  async function basculer() {
    const a = audio.current;
    if (!a) return;
    if (a.paused) {
      try {
        await a.play();
      } catch {
        setEtat("absent");
      }
    } else a.pause();
  }

  return (
    <div className="lecteur-audio">
      <button
        type="button"
        className="lecteur-bouton"
        aria-label={t(etat === "lecture" ? "audio.pause" : enWolof ? "audio.ecouterWo" : "audio.ecouter", { s: String(secondes) })}
        onClick={basculer}
      >
        {etat === "lecture" ? (
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" /></svg>
        ) : (
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4.5v15a1 1 0 0 0 1.5.9l12-7.5a1 1 0 0 0 0-1.8l-12-7.5A1 1 0 0 0 7 4.5z" /></svg>
        )}
      </button>
      <span className="lecteur-texte">
        <strong>{t(enWolof ? "audio.titreWo" : "audio.titre")}</strong>
        <span>{duree ? `${etat === "lecture" ? `${minuteur(ecoule)} / ` : ""}${minuteur(duree)} · ${t("audio.lue")}` : t("audio.lue")}</span>
      </span>
      <audio
        ref={audio}
        src={url}
        preload="metadata"
        onLoadedMetadata={(e) => Number.isFinite(e.currentTarget.duration) && setDuree(e.currentTarget.duration)}
        onTimeUpdate={(e) => setEcoule(e.currentTarget.currentTime)}
        onPlay={() => setEtat("lecture")}
        onPause={() => setEtat("pret")}
        onEnded={() => { setEtat("pret"); setEcoule(0); }}
        onError={() => setEtat("absent")}
      />
    </div>
  );
}
