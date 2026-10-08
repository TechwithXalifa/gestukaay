import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

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
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
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
