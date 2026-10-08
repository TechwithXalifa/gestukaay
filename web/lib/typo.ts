/**
 * Typographie française (7.4) : espace insécable avant « ? ! : ; » et à l'intérieur des guillemets,
 * pour qu'un signe ne parte jamais seul à la ligne (« Kolda » puis « ? » sur la ligne suivante).
 * Ne touche pas aux adresses (« https:// » n'a pas d'espace).
 */
export function insecables(texte: string): string {
  return chiffres(texte)
    .replace(/ ([?!:;»])/g, " $1")
    .replace(/« /g, "« ");
}

/**
 * Nombres lisibles : l'espace fine insécable entre les milliers (« 2 463 677 », U+202F) ne mesure
 * que 2 px dans Bricolage et Unbounded, et « 2463677 » se lisait d'un bloc (revue UI du 08/10).
 * On la remplace par une espace insécable ordinaire (U+00A0), toujours insécable mais visible.
 * Seulement entre deux chiffres : le reste du texte ne change pas.
 * Pas de lookbehind (?<=) : Safari ne le lit que depuis iOS 16.4, et avant, tout le JS est rejeté.
 */
export function chiffres(texte: string): string {
  return texte.replace(/(\d)\u202f(?=\d)/g, "$1\u00a0");
}

const entiers = new Intl.NumberFormat("fr-FR");

/** Nombre entier formaté par le site (catalogue, back-office), milliers lisibles comme ci-dessus. */
export function nombre(n: number): string {
  return chiffres(entiers.format(n));
}
