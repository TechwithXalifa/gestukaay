import { expect, test } from "@playwright/test";
import { accessible } from "./outils";

// « Ma région en chiffres » et comparaison de deux zones, sur le faux moteur : seul le taux de pauvreté y a des
// séries (Sénégal, Dakar, Kolda).

test("ma région en chiffres : on choisit une région sur le schéma", async ({ page }) => {
  await page.goto("/zones");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Ma région en chiffres");
  await expect(page.getByRole("navigation", { name: "Choisissez une région" }).getByRole("link")).toHaveCount(14);
  await accessible(page, "régions");
  await page.getByRole("link", { name: "Kolda" }).click();
  await expect(page).toHaveURL(/\/zones\/SN-KD$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Kolda en chiffres");
});

test("fiche d'une région : valeur, période, rang, source et lien vers Explorer", async ({ page }) => {
  await page.goto("/zones/SN-KD");
  const carte = page.locator(".chiffre-cle").filter({ hasText: "Taux de pauvreté" });
  await expect(carte).toContainText("62,5");
  await expect(carte).toContainText("en 2022");
  await expect(carte).toContainText("Valeur la plus élevée des 2 régions");
  await expect(carte).toContainText("EHCVM");
  await expect(page).toHaveTitle("Kolda en chiffres · Gëstukaay");
  await accessible(page, "fiche d'une région");
  await carte.getByRole("link", { name: "Voir l'évolution" }).click();
  await expect(page).toHaveURL(/\/explorer\?indicateur=jcvcajc\.taux-de-pauvrete&zones=SN,SN-KD$/);
});

test("fiche d'une zone inconnue : message clair", async ({ page }) => {
  await page.goto("/zones/XX");
  await expect(page.getByRole("heading", { name: "Cette zone n'a pas de fiche." })).toBeVisible();
});

test("comparer deux zones : côte à côte, dans l'adresse", async ({ page }) => {
  await page.goto("/zones");
  await page.getByLabel("Première zone").selectOption("SN-DK");
  await page.getByLabel("Deuxième zone").selectOption("SN-KD");
  await page.getByRole("button", { name: "Comparer" }).click();
  await expect(page).toHaveURL(/\/zones\/comparer\?a=SN-DK&b=SN-KD$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Dakar et Kolda");
  const ligne = page.getByRole("row", { name: /Taux de pauvreté/ });
  await expect(ligne).toContainText("9,3");
  await expect(ligne).toContainText("62,5");
  await accessible(page, "comparaison de deux zones");

  await page.getByLabel("Deuxième zone").selectOption("SN");
  await expect(page).toHaveURL(/b=SN$/);
  await expect(page.getByRole("row", { name: /Taux de pauvreté/ })).toContainText("37,5");
});
