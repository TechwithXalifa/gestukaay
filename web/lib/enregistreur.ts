/**
 * Enregistrement de la question à voix haute (décision 0004 §1, 7.3) :
 * WebM ou OGG Opus (seuls formats du contrat), arrêt automatique après 2 s de
 * silence une fois que la personne a parlé, 60 s au plus. Rien n'est gardé
 * sur l'appareil : le Blob part vers /v1/transcrire puis est oublié.
 */

export const SILENCE_MS = 2000;
export const DUREE_MAX_MS = 60_000;
// Sans un mot pendant ce délai, on s'arrête : l'écran proposera de réessayer
const ATTENTE_PAROLE_MS = 8000;
const SEUIL_PAROLE = 0.04;
const SEUIL_SILENCE = 0.02;

export type ErreurMicro = "refuse" | "indisponible" | "format";

export type Enregistrement = {
  arreter: () => void; // fin normale : la promesse `audio` se résout
  annuler: () => void; // abandon : rien n'est envoyé
  audio: Promise<Blob | null>; // null si annulé
};

/** Premier format Opus que le navigateur sait produire, ou null. */
export function formatAudio(): string | null {
  if (typeof MediaRecorder === "undefined") return null;
  return ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"].find((f) =>
    MediaRecorder.isTypeSupported(f),
  ) ?? null;
}

export async function enregistrer(
  surNiveau: (niveau: number, ecouleMs: number) => void,
): Promise<Enregistrement> {
  const mime = formatAudio();
  if (!mime) throw "format" satisfies ErreurMicro;
  if (!navigator.mediaDevices?.getUserMedia) throw "indisponible" satisfies ErreurMicro;

  let flux: MediaStream;
  try {
    flux = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  } catch (e) {
    const nom = e instanceof DOMException ? e.name : "";
    throw (nom === "NotAllowedError" || nom === "SecurityError" ? "refuse" : "indisponible") satisfies ErreurMicro;
  }

  const contexte = new AudioContext();
  // Certains navigateurs créent le contexte en pause : sans lui, aucun niveau mesuré
  await contexte.resume().catch(() => {});
  const analyseur = contexte.createAnalyser();
  analyseur.fftSize = 1024;
  contexte.createMediaStreamSource(flux).connect(analyseur);
  const echantillons = new Float32Array(analyseur.fftSize);

  const enregistreur = new MediaRecorder(flux, { mimeType: mime, audioBitsPerSecond: 24_000 });
  const morceaux: Blob[] = [];
  enregistreur.ondataavailable = (e) => e.data.size && morceaux.push(e.data);

  let annule = false;
  const debut = performance.now();
  let aParle = false;
  let silenceDepuis: number | null = null;
  let minuteur = 0;

  const audio = new Promise<Blob | null>((resoudre) => {
    enregistreur.onstop = () => {
      clearInterval(minuteur);
      flux.getTracks().forEach((t) => t.stop());
      contexte.close().catch(() => {});
      resoudre(annule || !aParle ? null : new Blob(morceaux, { type: mime.split(";")[0] }));
    };
  });

  const arreter = () => enregistreur.state !== "inactive" && enregistreur.stop();

  minuteur = window.setInterval(() => {
    analyseur.getFloatTimeDomainData(echantillons);
    let somme = 0;
    for (const v of echantillons) somme += v * v;
    const niveau = Math.sqrt(somme / echantillons.length);
    const maintenant = performance.now();
    const ecoule = maintenant - debut;
    surNiveau(niveau, ecoule);

    if (niveau > SEUIL_PAROLE) {
      aParle = true;
      silenceDepuis = null;
    } else if (aParle && niveau < SEUIL_SILENCE) {
      silenceDepuis ??= maintenant;
      if (maintenant - silenceDepuis >= SILENCE_MS) arreter();
    }
    if (ecoule >= DUREE_MAX_MS || (!aParle && ecoule >= ATTENTE_PAROLE_MS)) arreter();
  }, 100);

  enregistreur.start(250);
  return {
    arreter,
    annuler: () => {
      annule = true;
      arreter();
    },
    audio,
  };
}
