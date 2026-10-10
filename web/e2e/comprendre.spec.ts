import { expect, test } from "@playwright/test";
import { accessible, poser } from "./outils";

// « Explique-moi simplement » : sous une réponse, ce que mesure l'indicateur et les mots utiles ; le glossaire.

test("comprendre ce chiffre : définition (ou son absence), mots utiles, liens", async ({ page }) => {
  await poser(page, "Combien d'habitants à Thiès ?");
  const bouton = page.getByRole("button", { name: "Comprendre ce chiffre" });
  await expect(bouton).toHaveAttribute("aria-expanded", "false");
  await bouton.click();
  await expect(bouton).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("heading", { name: /Ce que mesure/ })).toBeVisible();
  // Faux moteur : pas de fiche pour la population, la réponse le dit au lieu d'inventer une définition
  await expect(page.getByText("Le portail de l'ANSD ne publie pas de définition pour cet indicateur.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Recensement (RGPH)" })).toHaveAttribute("href", "/glossaire#recensement");
  await accessible(page, "comprendre ce chiffre");
  await page.getByRole("link", { name: "Tout le glossaire" }).click();
  await expect(page).toHaveURL(/\/glossaire$/);
});

test("glossaire : liste triée, recherche et ancres", async ({ page }) => {
  await page.goto("/glossaire");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Glossaire : les mots de la statistique");
  await accessible(page, "glossaire");
  await page.getByRole("searchbox", { name: "Chercher un mot" }).fill("gini");
  await expect(page.locator(".glossaire dt")).toHaveText(["Indice de Gini"]);
  await expect(page.getByRole("status").filter({ hasText: "mot" })).toHaveText("1 mot");
  await page.getByRole("searchbox", { name: "Chercher un mot" }).fill("");
  await page.goto("/glossaire#taux-brut-de-scolarisation"); // même page : seule l'ancre change
  await expect(page.locator("#taux-brut-de-scolarisation")).toContainText("peut dépasser 100 %");
});
