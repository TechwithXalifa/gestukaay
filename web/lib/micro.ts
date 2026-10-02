export type AccesMicro = "accorde" | "refuse" | "indisponible";

/**
 * Demande l'accès au micro. On libère le micro tout de suite : rien n'est
 * enregistré tant que le parcours d'écoute (contrat v1.1.0, /v1/transcrire)
 * n'est pas branché.
 */
export async function demanderMicro(): Promise<AccesMicro> {
  if (!navigator.mediaDevices?.getUserMedia) return "indisponible";
  try {
    const flux = await navigator.mediaDevices.getUserMedia({ audio: true });
    flux.getTracks().forEach((t) => t.stop());
    return "accorde";
  } catch (e) {
    const nom = e instanceof DOMException ? e.name : "";
    return nom === "NotAllowedError" || nom === "SecurityError" ? "refuse" : "indisponible";
  }
}
