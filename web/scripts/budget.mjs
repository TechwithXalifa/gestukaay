// Budget de performance (cahier 7.6) : JavaScript initial ≤ 150 Ko compressé, par page.
// À lancer après `next build` :  npm run budget
// Compte, pour chaque page, les fichiers chargés au démarrage (runtime partagé, layouts,
// page), compressés en gzip. Les polyfills (nomodule) ne sont pas chargés par les
// navigateurs récents : ils ne comptent pas.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const BUDGET_KO = 150;
const NEXT = join(import.meta.dirname, "..", ".next");
const app = JSON.parse(readFileSync(join(NEXT, "app-build-manifest.json"), "utf8")).pages;
const build = JSON.parse(readFileSync(join(NEXT, "build-manifest.json"), "utf8"));

const tailles = new Map();
function ko(fichier) {
  if (!tailles.has(fichier)) tailles.set(fichier, gzipSync(readFileSync(join(NEXT, fichier)), { level: 9 }).length / 1024);
  return tailles.get(fichier);
}

/** Layouts qui enveloppent une page : « /admin/journal/page » -> « /layout », « /admin/layout »… */
function layouts(page) {
  const morceaux = page.split("/").slice(1, -1);
  return ["/layout", ...morceaux.map((_, i) => `/${morceaux.slice(0, i + 1).join("/")}/layout`)].filter((l) => app[l]);
}

let depasse = false;
console.log(`JavaScript initial par page (gzip), budget ${BUDGET_KO} Ko :`);
for (const page of Object.keys(app).filter((p) => p.endsWith("/page")).sort()) {
  const fichiers = new Set([...build.rootMainFiles, ...layouts(page).flatMap((l) => app[l]), ...app[page]]);
  const total = [...fichiers].filter((f) => f.endsWith(".js")).reduce((s, f) => s + ko(f), 0);
  const ok = total <= BUDGET_KO;
  depasse ||= !ok;
  console.log(`  ${ok ? "ok " : "TROP"}  ${total.toFixed(1).padStart(6)} Ko  ${page.replace(/\/page$/, "") || "/"}`);
}
if (depasse) {
  console.error(`\nBudget dépassé : une page charge plus de ${BUDGET_KO} Ko de JavaScript au démarrage (7.6).`);
  process.exit(1);
}
