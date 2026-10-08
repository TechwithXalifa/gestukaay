import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";
import { COMPTE_ADMIN } from "../playwright.config";

/** Aucune violation WCAG 2.1 A et AA détectable automatiquement (cahier, accessibilité). */
export async function accessible(page: Page, ecran: string) {
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

/** Connexion au back-office avec le compte des tests (créé au lancement de l'API). */
export async function seConnecter(page: Page) {
  await page.getByLabel("Identifiant").fill(COMPTE_ADMIN.identifiant);
  await page.getByLabel("Mot de passe").fill(COMPTE_ADMIN.motDePasse);
}
