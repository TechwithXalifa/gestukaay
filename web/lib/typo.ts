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

// Tout nombre que le site formate lui-même passe par ici, une seule fois (revue de KBD sur la #155).
const formats = new Map<string, Intl.NumberFormat>();
function format(style: "decimal" | "percent", decimales: number): Intl.NumberFormat {
  const cle = `${style}-${decimales}`;
  let f = formats.get(cle);
  if (!f) formats.set(cle, (f = new Intl.NumberFormat("fr-FR", { style, maximumFractionDigits: decimales })));
  return f;
}

/** Nombre formaté par le site (catalogue, graphiques, back-office), milliers lisibles comme ci-dessus. */
export function nombre(n: number, decimales = 0): string {
  return chiffres(format("decimal", decimales).format(n));
}

/**
 * « 89,2 % ». L'espace avant % est toujours une insécable ordinaire : selon leur version, Node et
 * les navigateurs mettent une fine ou une ordinaire, et le texte rendu par le serveur doit être
 * celui du navigateur.
 */
export function pourcentage(x: number, decimales = 1): string {
  return chiffres(format("percent", decimales).format(x)).replace(/\s%$/, `${String.fromCharCode(0xa0)}%`);
}

/**
 * Titre de publication lisible : sans le numéro de tableau que le portail met devant
 * (« 10.1_Indices de pauvreté », « 18.3-b_Résultats… » → « Indices de pauvreté »). Affichage seulement :
 * la citation et les exports gardent le titre tel que publié.
 */
export function titreSource(titre: string): string {
  const net = titre.replace(/^\s*(?:\d+(?:\.\d+)+(?:-[a-z])?\s*[_\u2013-]|\d+(?:-[a-z])?_)\s*/i, "");
  return net ? net.charAt(0).toUpperCase() + net.slice(1) : titre;
}
