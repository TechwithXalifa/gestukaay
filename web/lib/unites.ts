import type { Resultat } from "@contracts/ask_response";

// Même règle que unite_ambigue (engine/…/gabarits.py), à garder identique : « unité non précisée par la source »
// (0031) seulement quand le nombre nu peut se lire de travers. Un compte évident (entier d'au moins 100, libellé
// sans taux, part, prix… : « 21 426 accidents ») n'en a pas besoin (KBD, 08/10).
const PAS_UN_COMPTE = /\b(taux|part|proportion|pourcentage|indice|ratio|moyenne?|densite|rendement|prix|cout|montant|valeur|depense|budget|recette|salaire|revenu|esperance|duree|superficie|production|quantite|poids|volume)\b/;

function normaliser(texte: string): string {
  return texte.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/['’`]/g, "");
}

export function uniteAmbigue(v: Pick<Resultat, "unite" | "valeur" | "indicateur">): boolean {
  if (v.unite?.trim()) return false;
  const compte = Number.isInteger(v.valeur) && v.valeur >= 100 && !PAS_UN_COMPTE.test(normaliser(v.indicateur.libelle));
  return !compte;
}
