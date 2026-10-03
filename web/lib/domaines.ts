/**
 * Domaines du socle (socle/referentiels/domaines.csv, décision 0005).
 * À garder aligné sur ce fichier si KBD ajoute ou renomme un domaine.
 * Les 6 domaines des questions types du cahier viennent en tête de
 * l'accueil, avec une question d'exemple qui se pose en un clic.
 */
export const DOMAINES_PRINCIPAUX: { nom: string; exemple: string }[] = [
  { nom: "Démographie", exemple: "Combien d'habitants à Thiès ?" },
  { nom: "Emploi et chômage", exemple: "Chômage à Dakar et à Thiès en 2024" },
  { nom: "Prix", exemple: "Combien coûte le kilo de riz brisé au détail ?" },
  { nom: "Éducation", exemple: "Quel est le taux de scolarisation à Dakar ?" },
  { nom: "Santé", exemple: "Quelle proportion des enfants sont complètement vaccinés à Kolda ?" },
  { nom: "Pauvreté", exemple: "Quel est le taux de pauvreté à Kolda ?" },
];

export const TOUS_LES_DOMAINES: string[] = [
  "Agriculture", "Banque et finance", "Commerce extérieur", "Comptes nationaux et PIB", "Culture",
  "Démographie", "Eau", "Économie", "Éducation", "Élevage", "Emploi et chômage", "Énergie",
  "Enseignement supérieur", "Entreprises", "Environnement", "Finances publiques", "Genre",
  "Gouvernance", "Habitat", "Justice", "Migration", "Mines", "Pauvreté", "Pêche", "Prix", "Santé",
  "Secours et assistance sociale", "Sécurité alimentaire", "Sports", "Télécommunications et TIC",
  "Tourisme", "Transport",
];
