import { expect, test } from "@playwright/test";
import { accessible, seConnecter } from "./outils";

// API publique : page développeurs, et clés délivrées puis révoquées dans le back-office.

test("page développeurs : adresse, routes, exemples et règles d'usage", async ({ page }) => {
  await page.goto("/developpeurs");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("API publique : les chiffres officiels dans vos applications");
  await expect(page.locator(".dev-code-ligne")).toHaveText("http://localhost:8000");
  await expect(page.getByRole("link", { name: /Documentation interactive/ })).toHaveAttribute("href", "http://localhost:8000/docs");
  await expect(page.getByRole("region", { name: "Les routes principales" }).getByRole("row")).toHaveCount(8);
  await expect(page.getByRole("heading", { name: "Règles d'usage" })).toBeVisible();
  await accessible(page, "développeurs");
});

test("clés d'API : délivrer, utiliser, révoquer", async ({ page, request }) => {
  await page.goto("/admin/cles");
  await seConnecter(page);
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByRole("heading", { name: "Clés de l'API publique" })).toBeVisible();

  const nom = `Essai e2e ${Date.now()}`;
  await page.getByLabel("Partenaire :").fill(nom);
  await page.getByRole("button", { name: "Délivrer une clé" }).click();
  const cle = (await page.locator(".admin-cle").textContent()) ?? "";
  expect(cle).toMatch(/^gk_/);
  await expect(page.getByRole("row", { name: new RegExp(nom) })).toContainText("Active");
  await accessible(page, "clés d'API");

  const avec = await request.get("http://localhost:8000/v1/indicators", { headers: { "X-Gestukaay-Cle": cle } });
  expect(avec.status()).toBe(200);

  page.once("dialog", (d) => d.accept());
  await page.getByRole("row", { name: new RegExp(nom) }).getByRole("button", { name: "Révoquer" }).click();
  await expect(page.getByRole("row", { name: new RegExp(nom) })).toContainText("Révoquée");
  const apres = await request.get("http://localhost:8000/v1/indicators", { headers: { "X-Gestukaay-Cle": cle } });
  expect(apres.status()).toBe(401);
});
