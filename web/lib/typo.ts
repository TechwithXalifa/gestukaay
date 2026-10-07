/**
 * Typographie française (7.4) : espace insécable avant « ? ! : ; » et à l'intérieur des guillemets,
 * pour qu'un signe ne parte jamais seul à la ligne (« Kolda » puis « ? » sur la ligne suivante).
 * Ne touche ni aux nombres (déjà formatés par le moteur) ni aux adresses (« https:// » n'a pas d'espace).
 */
export function insecables(texte: string): string {
  return texte
    .replace(/ ([?!:;»])/g, " $1")
    .replace(/« /g, "« ");
}
