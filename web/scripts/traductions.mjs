// Couverture de l'interface wolof : npm run traductions
// Affiche le pourcentage traduit, puis les textes français restant à confier
// au locuteur natif (tâche #26), au format « clé ; texte » prêt à copier.
import { readFileSync } from "node:fs";

const lire = (f) => readFileSync(new URL(`../i18n/${f}`, import.meta.url), "utf8");
const paires = (src) => [...src.matchAll(/^\s*"([\w.]+)":\s*"((?:[^"\\]|\\.)*)"/gm)].map((m) => [m[1], m[2]]);

const fr = paires(lire("fr.ts"));
const wo = new Set(paires(lire("wo.ts")).map(([k]) => k));
const manquants = fr.filter(([k]) => !wo.has(k));

console.log(`Interface wolof : ${fr.length - manquants.length} / ${fr.length} textes validés.`);
if (manquants.length) {
  console.log("\nÀ traduire (clé ; texte français) :");
  for (const [k, t] of manquants) console.log(`${k} ; ${t}`);
}
