import { imageReponse } from "@/lib/image-reponse";
import { lireReponseServeur } from "@/lib/lecture-serveur";

/** Export « Image » d'une réponse (EF-36) : la même image que l'aperçu de partage, à télécharger. */
export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const rep = await lireReponseServeur(id);
  if (!rep) return new Response("Réponse introuvable", { status: 404 });
  const nom = id.replace(/[^\w-]/g, "_");
  return imageReponse(rep, {
    "Content-Disposition": `attachment; filename="gestukaay-${nom}.png"`,
    "Cache-Control": "public, max-age=3600",
  });
}
