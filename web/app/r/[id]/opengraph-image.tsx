import { imageReponse, TAILLE } from "@/lib/image-reponse";
import { lireReponseServeur } from "@/lib/lecture-serveur";

// Aperçu d'un lien /r/… collé dans WhatsApp, Telegram ou un réseau social (Open Graph) : le chiffre et sa source
export const size = TAILLE;
export const contentType = "image/png";
export const alt = "Le chiffre officiel, avec sa source et sa date";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  return imageReponse(await lireReponseServeur((await params).id));
}
