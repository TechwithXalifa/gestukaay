import { expect, test } from "@playwright/test";
import { JETON_ADMIN } from "../playwright.config";
import { accessible, poser } from "./outils";

test("domaines : la liste complète", async ({ page }) => {
  await page.goto("/domaines");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("32 domaines");
  await accessible(page, "domaines");
});

test("hors ligne : l'état s'affiche et la question est bloquée", async ({ page, context }) => {
  await page.goto("/");
  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));
  await expect(page.getByText("Vous êtes hors ligne.")).toBeVisible();
  await accessible(page, "hors ligne");
  await context.setOffline(false);
});

test("bascule FR/WO : l'état est annoncé et le bandeau prévient", async ({ page }) => {
  await page.goto("/");
  const wo = page.getByRole("button", { name: "WO", exact: true });
  await wo.click();
  await expect(wo).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("status").filter({ hasText: "wolof" })).toBeVisible();
  await accessible(page, "accueil en wolof");
});

test("journal des requêtes : jeton, filtres et détail", async ({ page }) => {
  await poser(page, "Combien de personnes parlent sérère au Sénégal ?");
  await page.goto("/admin/journal");
  await accessible(page, "journal, connexion");
  await page.getByLabel("Jeton d'administration").fill(JETON_ADMIN);
  await page.getByRole("button", { name: "Ouvrir le journal" }).click();
  await expect(page.getByRole("heading", { name: "Journal des requêtes" })).toBeVisible();

  await page.getByLabel("Issue :").selectOption("aucune");
  const ligne = page.getByRole("button", { name: /sérère/ }).first();
  await ligne.click();
  await expect(page.getByRole("complementary", { name: "Détail de la requête" })).toContainText("Refus");
  await accessible(page, "journal");
});

test("titres de page propres à chaque écran (WCAG 2.4.2)", async ({ page }) => {
  await page.goto("/situer");
  await expect(page).toHaveTitle("Où je me situe · Gëstukaay");
  await page.goto("/domaines");
  await expect(page).toHaveTitle("Domaines de données · Gëstukaay");
  await poser(page, "Combien d'habitants à Thiès ?");
  await expect(page).toHaveTitle("Combien d'habitants à Thiès ? · Gëstukaay");
});

test("lien d'évitement : le premier Tab mène au contenu (WCAG 2.4.1)", async ({ page, isMobile }) => {
  test.skip(isMobile, "navigation clavier : poste de bureau");
  await page.goto("/");
  await page.keyboard.press("Tab");
  const lien = page.getByRole("link", { name: "Aller au contenu" });
  await expect(lien).toBeFocused();
  await expect(lien).toBeInViewport();
  await page.keyboard.press("Enter");
  await expect(page.locator("main#contenu")).toBeFocused();
});

test("fenêtre « Je vous écoute » : focus dedans, Échap ferme, focus rendu au micro", async ({ page, isMobile }) => {
  test.skip(isMobile, "faux micro configuré sur le projet bureau");
  await page.goto("/");
  const micro = page.getByRole("button", { name: "Poser la question à voix haute" });
  await micro.click();
  const fenetre = page.getByRole("dialog");
  await expect(fenetre).toBeVisible();
  await expect(fenetre.locator(":focus")).toHaveCount(1);
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press("Tab");
    await expect(fenetre.locator(":focus")).toHaveCount(1); // Tab ne sort pas de la fenêtre
  }
  await accessible(page, "écoute");
  await page.keyboard.press("Escape");
  await expect(fenetre).toBeHidden();
  await expect(micro).toBeFocused();
});


test("mode sombre : contrastes sur l'accueil, la réponse et le refus", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await accessible(page, "accueil, mode sombre");
  await poser(page, "Combien d'habitants à Thiès ?");
  await accessible(page, "réponse, mode sombre");
  await poser(page, "Combien de personnes parlent sérère au Sénégal ?");
  await accessible(page, "refus, mode sombre");
});
