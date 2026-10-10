/**
 * Glossaire des mots de la statistique, en langage simple (« Explique-moi simplement »). Ce sont des
 * explications générales, jamais des chiffres : aucun nombre du socle n'est écrit ici. La définition exacte
 * d'un indicateur reste celle publiée par le portail (fiche indicateur), citée telle quelle.
 *
 * `cles` : morceaux de texte (minuscules, sans accents) qui, trouvés dans le libellé de l'indicateur, son unité,
 * l'explication ou la source d'une réponse, font apparaître le mot sous « Comprendre ce chiffre ».
 * Textes en français : la version wolof est à écrire par le locuteur natif (décision 0009).
 */
export type Mot = { id: string; mot: string; definition: string; cles: string[] };

export const GLOSSAIRE: Mot[] = [
  {
    id: "taux",
    mot: "Taux, pourcentage",
    definition: "Une part ramenée à 100. Un taux de 25 % veut dire 25 personnes (ou ménages) sur 100.",
    cles: ["taux", "%", "proportion", "pourcentage", "part "],
  },
  {
    id: "point-de-pourcentage",
    mot: "Point de pourcentage",
    definition: "L'écart entre deux pourcentages. Passer de 20 % à 25 %, c'est gagner 5 points de pourcentage.",
    cles: [],
  },
  {
    id: "moyenne",
    mot: "Moyenne",
    definition: "On additionne toutes les valeurs, puis on divise par leur nombre. Quelques valeurs très élevées suffisent à tirer la moyenne vers le haut.",
    cles: ["moyen", "moyenne"],
  },
  {
    id: "mediane",
    mot: "Médiane",
    definition: "La valeur du milieu : la moitié des cas est au-dessous, l'autre moitié au-dessus. Elle bouge moins que la moyenne avec les valeurs extrêmes.",
    cles: ["median"],
  },
  {
    id: "indice",
    mot: "Indice",
    definition: "Un nombre qui compare une valeur à une référence. Avec une base 100, un indice de 110 veut dire 10 % de plus que l'année de référence.",
    cles: ["indice"],
  },
  {
    id: "inflation",
    mot: "Indice des prix et inflation",
    definition: "L'indice des prix à la consommation suit le prix d'un panier de produits achetés par les ménages. L'inflation, c'est sa hausse sur un an.",
    cles: ["indice des prix", "ihpc", "inflation", "prix a la consommation"],
  },
  {
    id: "chomage",
    mot: "Taux de chômage",
    definition: "La part des personnes sans emploi qui en cherchent un, parmi les personnes en âge de travailler qui travaillent ou cherchent du travail. Ce n'est pas une part de toute la population.",
    cles: ["chomage", "chomeur"],
  },
  {
    id: "pauvrete",
    mot: "Taux de pauvreté",
    definition: "La part des personnes qui vivent dans un ménage dont la consommation par personne est sous le seuil de pauvreté.",
    cles: ["pauvrete", "pauvre"],
  },
  {
    id: "seuil-de-pauvrete",
    mot: "Seuil de pauvreté",
    definition: "Le niveau de consommation par personne et par an en dessous duquel on est considéré comme pauvre. Il couvre la nourriture de base et quelques dépenses essentielles.",
    cles: ["seuil de pauvrete", "pauvrete"],
  },
  {
    id: "consommation-par-tete",
    mot: "Consommation par tête",
    definition: "Tout ce que le ménage consomme en un an (nourriture, logement, transport…), divisé par le nombre de personnes du ménage.",
    cles: ["consommation moyenne par tete", "par tete", "par personne et par an"],
  },
  {
    id: "gini",
    mot: "Indice de Gini",
    definition: "Il mesure les inégalités, de 0 à 1 : 0 si tout le monde a le même niveau de vie, plus il se rapproche de 1, plus les écarts sont grands.",
    cles: ["gini", "inegalite"],
  },
  {
    id: "taux-brut-de-scolarisation",
    mot: "Taux brut de scolarisation",
    definition: "Le nombre d'élèves inscrits dans un cycle, quel que soit leur âge, rapporté au nombre d'enfants qui ont l'âge officiel de ce cycle. Il peut dépasser 100 % : des élèves plus âgés ou plus jeunes sont aussi comptés.",
    cles: ["taux brut de scolarisation", "scolarisation"],
  },
  {
    id: "urbanisation",
    mot: "Taux d'urbanisation",
    definition: "La part de la population qui vit en ville (en milieu urbain).",
    cles: ["urbanisation"],
  },
  {
    id: "fecondite",
    mot: "Nombre moyen d'enfants par femme",
    definition: "Le nombre d'enfants qu'une femme aurait au cours de sa vie si elle suivait les comportements de fécondité observés cette année-là. On parle aussi d'indice synthétique de fécondité.",
    cles: ["enfants par femme", "fecondite"],
  },
  {
    id: "mortalite-infanto-juvenile",
    mot: "Mortalité des enfants de moins de 5 ans",
    definition: "Le nombre d'enfants qui meurent avant leurs 5 ans, pour 1 000 enfants nés vivants.",
    cles: ["moins de 5 ans", "infanto", "mortalite infantile", "mortalite"],
  },
  {
    id: "vaccination",
    mot: "Enfants complètement vaccinés",
    definition: "La part des enfants de 12 à 23 mois qui ont reçu tous les vaccins prévus par le calendrier vaccinal.",
    cles: ["vaccin"],
  },
  {
    id: "menage",
    mot: "Ménage",
    definition: "Un groupe de personnes qui vivent sous le même toit, partagent leurs repas et une partie de leurs ressources. Une personne seule forme aussi un ménage.",
    cles: ["menage"],
  },
  {
    id: "milieu",
    mot: "Milieu urbain, milieu rural",
    definition: "Urbain : les villes. Rural : les villages et la campagne. Les deux sont définis par l'ANSD pour le recensement.",
    cles: ["urbain", "rural", "milieu"],
  },
  {
    id: "zones",
    mot: "Région, département, académie",
    definition: "Le Sénégal compte 14 régions, découpées en départements. L'académie (inspection d'académie) est le découpage de l'éducation : une région peut en compter plusieurs, comme Dakar.",
    cles: ["academie", "departement"],
  },
  {
    id: "recensement",
    mot: "Recensement (RGPH)",
    definition: "Le Recensement général de la population et de l'habitat compte toutes les personnes et tous les logements du pays. Le cinquième (RGPH-5) a eu lieu en 2023.",
    cles: ["rgph", "recensement general"],  // pas « recensement » seul : le recensement scolaire n'en est pas un
  },
  {
    id: "enquete",
    mot: "Enquête par sondage",
    definition: "On interroge une partie des ménages, choisie au hasard, pour connaître l'ensemble. Le résultat est très proche de la réalité, à une petite marge d'erreur près. Exemples : EHCVM (niveau de vie), EDS (santé), ENES (emploi).",
    cles: ["ehcvm", "eds", "enes", "enquete"],
  },
  {
    id: "projection",
    mot: "Projection",
    definition: "Un chiffre calculé par l'ANSD pour une année à venir, à partir d'hypothèses (naissances, décès, migrations). Ce n'est pas une valeur observée : Gëstukaay l'indique toujours.",
    cles: ["projection"],
  },
  {
    id: "estimation",
    mot: "Estimation",
    definition: "Un chiffre calculé par le producteur officiel quand il ne peut pas être mesuré directement. Il est signalé comme tel, à côté de la valeur.",
    cles: ["estimation"],
  },
  {
    id: "pib",
    mot: "PIB (produit intérieur brut)",
    definition: "La valeur de tout ce qui est produit dans le pays en un an (biens et services), une fois retiré ce qui a servi à le produire.",
    cles: ["pib", "produit interieur brut"],
  },
  {
    id: "prix-courants-constants",
    mot: "Prix courants, prix constants",
    definition: "À prix courants, les montants sont ceux de chaque année. À prix constants, la hausse des prix est retirée : on voit si l'on produit vraiment plus.",
    cles: ["prix courants", "prix constants", "en volume"],
  },
];

/** Minuscules sans accents, comme le moteur : « Pauvreté » et « pauvrete » se rejoignent. */
export const normaliser = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

/** Les mots du glossaire utiles pour comprendre un texte (libellé, unité, explication, source), sans doublon. */
export function motsUtiles(texte: string, max = 4): Mot[] {
  const t = normaliser(texte);
  // Le mot le plus précis d'abord : « taux brut de scolarisation » passe devant « taux »
  const precision = (m: Mot) => Math.max(0, ...m.cles.filter((c) => t.includes(c)).map((c) => c.length));
  return GLOSSAIRE.filter((m) => precision(m) > 0)
    .sort((a, b) => precision(b) - precision(a))
    .slice(0, max);
}
