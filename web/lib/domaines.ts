/**
 * Domaines du socle (socle/referentiels/domaines.csv, décision 0005).
 * À garder aligné sur ce fichier si KBD ajoute ou renomme un domaine.
 * Les 6 domaines des questions types du cahier viennent en tête de
 * l'accueil, avec une question d'exemple qui se pose en un clic ; Énergie et
 * Comptes nationaux complètent les deux lignes de quatre (questions vérifiées
 * sur le vrai moteur le 09/10 : réponse exacte, 84,3 % en 2023 et le PIB 2024).
 * `icone` : la clé de l'icône du domaine (components/icones.tsx).
 */
export type IconeDomaine = "demographie" | "emploi" | "prix" | "education" | "sante" | "pauvrete" | "energie" | "economie";
export const DOMAINES_PRINCIPAUX: { nom: string; exemple: string; icone: IconeDomaine }[] = [
  { nom: "Démographie", exemple: "Combien d'habitants à Thiès ?", icone: "demographie" },
  { nom: "Emploi et chômage", exemple: "Chômage à Dakar et à Thiès en 2024", icone: "emploi" },
  { nom: "Prix", exemple: "Combien coûte le kilo de riz brisé au détail ?", icone: "prix" },
  { nom: "Éducation", exemple: "Quel est le taux de scolarisation à Dakar ?", icone: "education" },
  { nom: "Santé", exemple: "Quelle proportion des enfants sont complètement vaccinés à Kolda ?", icone: "sante" },
  { nom: "Pauvreté", exemple: "Quel est le taux de pauvreté à Kolda ?", icone: "pauvrete" },
  { nom: "Énergie", exemple: "Quel est le taux d'électrification au Sénégal ?", icone: "energie" },
  { nom: "Comptes nationaux et PIB", exemple: "Quel est le PIB du Sénégal ?", icone: "economie" },
];

export const TOUS_LES_DOMAINES: string[] = [
  "Agriculture", "Banque et finance", "Commerce extérieur", "Comptes nationaux et PIB", "Culture",
  "Démographie", "Eau", "Économie", "Éducation", "Élevage", "Emploi et chômage", "Énergie",
  "Enseignement supérieur", "Entreprises", "Environnement", "Finances publiques", "Genre",
  "Gouvernance", "Habitat", "Justice", "Migration", "Mines", "Pauvreté", "Pêche", "Prix", "Santé",
  "Secours et assistance sociale", "Sécurité alimentaire", "Sports", "Télécommunications et TIC",
  "Tourisme", "Transport",
];
