import { expect, test } from "@playwright/test";
import { accessible, poser } from "./outils";

// « Mes chiffres » : réponses épinglées et dernières consultées, gardées sur l'appareil seulement.

test("épingler une réponse, la retrouver dans Mes chiffres, la télécharger, la retirer", async ({ page }) => {
  await poser(page, "Combien d'habitants à Thiès ?");
  const epingler = page.getByRole("button", { name: "Épingler" });
  await epingler.click();
  await expect(page.getByRole("status").filter({ hasText: "Ajouté à Mes chiffres" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Épinglé" })).toHaveAttribute("aria-pressed", "true");

  await page.goto("/mes-chiffres");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mes chiffres");
  const epingles = page.locator("section").filter({ has: page.getByRole("heading", { name: "Épinglés (1)" }) });
  await expect(epingles.getByRole("link")).toContainText("2 463 677");
  await accessible(page, "mes chiffres");

  // Tableur des chiffres épinglés, fabriqué dans le navigateur
  const [telechargement] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Télécharger en tableur" }).click(),
  ]);
  expect(telechargement.suggestedFilename()).toBe("gestukaay-mes-chiffres.csv");

  // Les espaces avant « ? » et dans les guillemets sont insécables (typographie) : le nom se cherche par motif
  await page.getByRole("button", { name: /^Retirer .*Thiès.* de Mes chiffres$/ }).click();
  await expect(page.getByRole("heading", { name: "Épinglés (0)" })).toBeVisible();
  await expect(page.getByText("Aucun chiffre épinglé.")).toBeVisible();
});

test("consultées récemment : oublier une réponse, effacer l'historique après confirmation", async ({ page }) => {
  await poser(page, "Combien d'habitants à Thiès ?");
  await page.goto("/mes-chiffres");
  const recentes = page.locator("section").filter({ has: page.getByRole("heading", { name: "Consultées récemment" }) });
  await expect(recentes.getByRole("link")).toHaveCount(1);
  await page.getByRole("button", { name: "Effacer l'historique" }).click();
  await page.getByRole("button", { name: "Oui, tout effacer" }).click();
  await expect(page.getByText("Aucune réponse consultée sur cet appareil.")).toBeVisible();
});
