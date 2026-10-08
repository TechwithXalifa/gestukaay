import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";
import { COMPTE_ADMIN } from "../playwright.config";

/** Aucune violation WCAG 2.1 A et AA détectable automatiquement (cahier, accessibilité). */
export async function accessible(page: Page, ecran: string) {
  // Les contrastes se mesurent sur l'état final : on attend la fin des apparitions et des
  // transitions (design system v2). Les animations sans fin (frise, micro) et celles liées au
  // défilement sont écartées, elles ne finissent jamais.
  await page.evaluate(() =>
    Promise.race([
      Promise.all(
        document
          .getAnimations()
          .filter((a) => a.timeline === document.timeline && a.effect?.getComputedTiming().iterations !== Infinity)
          .map((a) => a.finished.catch(() => undefined)),
      ),
      new Promise((fin) => setTimeout(fin, 3000)),
    ]),
  );
  // Pour mesurer un contraste hors de l'écran, axe fait défiler la page : l'en-tête flottant se cache
  // puis revient, et axe le lisait parfois à demi transparent. Pendant l'audit, « moins d'animations »
  // le garde en place et opaque (globals.css) : ses liens sont mesurés tels qu'on les voit.
  await page.emulateMedia({ reducedMotion: "reduce" });
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  await page.emulateMedia({ reducedMotion: null });
  const resume = violations.map(
    (v) => `${v.id} (${v.impact}) : ${v.help}\n    ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join("\n    ")}`,
  );
  expect(resume, `Accessibilité, écran « ${ecran} »`).toEqual([]);
}

/** Pose une question depuis l'accueil et attend la page réponse. */
export async function poser(page: Page, question: string) {
  await page.goto("/");
  await page.getByRole("textbox", { name: "Votre question" }).fill(question);
  await page.getByRole("button", { name: "Envoyer la question" }).click();
  await page.waitForURL(/\/r\/[\w-]+$/);
}

/** Connexion au back-office avec le compte des tests (créé au lancement de l'API). */
export async function seConnecter(page: Page) {
  await page.getByLabel("Identifiant").fill(COMPTE_ADMIN.identifiant);
  await page.getByLabel("Mot de passe").fill(COMPTE_ADMIN.motDePasse);
}
