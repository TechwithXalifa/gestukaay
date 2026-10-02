"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useLangue } from "@/i18n/langue";
import { transcrire } from "@/lib/api";
import { type Enregistrement, type ErreurMicro, enregistrer } from "@/lib/enregistreur";
import { Fleche, Micro, Tourne } from "./icones";

type Etat = "ecoute" | "transcription" | "verification" | "vide" | "erreur" | "format";
const BARRES = 24;

/**
 * État « Écoute » (7.3, maquette M-Ecoute, décision 0004 §1) : plein écran
 * sombre, onde, minuteur ; à l'arrêt, la transcription s'affiche et reste
 * modifiable avant l'envoi (US-09). Le texte n'apparaît pas pendant qu'on
 * parle : la transcription wolof ne fonctionne pas en continu.
 */
export function Ecoute({
  onEnvoyer,
  onFermer,
  onRefus,
}: {
  onEnvoyer: (question: string, transcriptionBrute: string, langue: "fr" | "wo") => void;
  onFermer: () => void;
  onRefus: () => void;
}) {
  const { t } = useLangue();
  const [etat, setEtat] = useState<Etat>("ecoute");
  const [niveaux, setNiveaux] = useState<number[]>(() => Array(BARRES).fill(0));
  const [secondes, setSecondes] = useState(0);
  const [texte, setTexte] = useState("");
  const [brute, setBrute] = useState("");
  const [langue, setLangue] = useState<"fr" | "wo">("fr");
  const enCours = useRef<Enregistrement | null>(null);

  const demarrer = useCallback(async () => {
    setEtat("ecoute");
    setSecondes(0);
    setNiveaux(Array(BARRES).fill(0));
    let rec: Enregistrement;
    try {
      rec = await enregistrer((niveau, ecoule) => {
        setNiveaux((n) => [...n.slice(1), Math.min(1, niveau * 8)]);
        setSecondes(Math.floor(ecoule / 1000));
      });
    } catch (e) {
      if ((e as ErreurMicro) === "refuse") onRefus();
      else setEtat((e as ErreurMicro) === "format" ? "format" : "erreur");
      return;
    }
    enCours.current = rec;
    const audio = await rec.audio;
    enCours.current = null;
    if (!audio) {
      setEtat((etat) => (etat === "ecoute" ? "vide" : etat));
      return;
    }
    setEtat("transcription");
    try {
      const r = await transcrire(audio);
      if (!r.transcription.trim()) return setEtat("vide");
      setTexte(r.transcription);
      setBrute(r.transcription);
      setLangue(r.langue);
      setEtat("verification");
    } catch {
      setEtat("erreur");
    }
  }, [onRefus]);

  useEffect(() => {
    demarrer();
    return () => enCours.current?.annuler();
  }, [demarrer]);

  // Échap = Annuler, comme le bouton
  useEffect(() => {
    const touche = (e: KeyboardEvent) => e.key === "Escape" && fermer();
    window.addEventListener("keydown", touche);
    return () => window.removeEventListener("keydown", touche);
  });

  function fermer() {
    enCours.current?.annuler();
    onFermer();
  }

  const minuteur = `0:${String(secondes).padStart(2, "0")}`;

  return (
    <div className="ecoute gk-dark" role="dialog" aria-modal="true" aria-labelledby="ecoute-titre">
      <div className="ecoute-haut">
        <button type="button" className="bouton-contour" aria-label={t("ecoute.annuler")} onClick={fermer}>
          ✕
        </button>
      </div>

      {etat === "ecoute" && (
        <div className="ecoute-centre" aria-live="polite">
          <p id="ecoute-titre" className="ecoute-titre">{t("ecoute.titre")}</p>
          <div className="ecoute-micro">
            <span className="pulse" aria-hidden="true" />
            <span className="pulse retard" aria-hidden="true" />
            <span className="ecoute-rond"><Micro taille={44} /></span>
          </div>
          <div className="onde" aria-hidden="true">
            {niveaux.map((n, i) => (
              <span key={i} style={{ height: `${8 + n * 64}px` }} />
            ))}
          </div>
          <p className="ecoute-aide"><strong>{minuteur}</strong> · {t("ecoute.arret")}</p>
        </div>
      )}

      {etat === "transcription" && (
        <div className="ecoute-centre" aria-live="polite" aria-busy="true">
          <p id="ecoute-titre" className="ecoute-titre"><Tourne taille={28} /> {t("ecoute.transcription")}</p>
        </div>
      )}

      {etat === "verification" && (
        <form
          className="ecoute-verif"
          onSubmit={(e) => {
            e.preventDefault();
            if (texte.trim().length >= 3) onEnvoyer(texte.trim(), brute, langue);
          }}
        >
          <label id="ecoute-titre" htmlFor="transcription" className="ecoute-titre">{t("ecoute.verifier")}</label>
          <textarea
            id="transcription"
            lang={langue}
            value={texte}
            onChange={(e) => setTexte(e.target.value)}
            maxLength={300}
            rows={3}
            autoFocus
          />
          <p className="ecoute-aide">{t("ecoute.corriger")}</p>
        </form>
      )}

      {(etat === "vide" || etat === "erreur" || etat === "format") && (
        <div className="ecoute-centre" role="alert">
          <p id="ecoute-titre" className="ecoute-titre">
            {t(etat === "vide" ? "ecoute.vide" : etat === "format" ? "ecoute.format" : "etat.service")}
          </p>
          <p className="ecoute-aide">{t(etat === "vide" ? "ecoute.videAide" : "ecoute.ecrire")}</p>
        </div>
      )}

      <div className="ecoute-bas">
        {etat === "ecoute" && (
          <>
            <button type="button" className="bouton-contour large" onClick={fermer}>{t("ecoute.annuler")}</button>
            <button type="button" className="bouton-feuille large" onClick={() => enCours.current?.arreter()}>
              <Fleche />{t("ecoute.terminer")}
            </button>
          </>
        )}
        {etat === "verification" && (
          <>
            <button type="button" className="bouton-contour large" onClick={demarrer}>
              <Micro />{t("ecoute.reenregistrer")}
            </button>
            <button
              type="button"
              className="bouton-feuille large"
              disabled={texte.trim().length < 3}
              onClick={() => onEnvoyer(texte.trim(), brute, langue)}
            >
              <Fleche />{t("ecoute.envoyer")}
            </button>
          </>
        )}
        {(etat === "vide" || etat === "erreur") && (
          <>
            <button type="button" className="bouton-contour large" onClick={fermer}>{t("ecoute.ecrireBouton")}</button>
            <button type="button" className="bouton-feuille large" onClick={demarrer}>
              <Micro />{t("etat.reessayer")}
            </button>
          </>
        )}
        {etat === "format" && (
          <button type="button" className="bouton-feuille large" onClick={fermer}>{t("ecoute.ecrireBouton")}</button>
        )}
      </div>
      <p className="ecoute-confidentialite">{t("ecoute.confidentialite")}</p>
    </div>
  );
}
