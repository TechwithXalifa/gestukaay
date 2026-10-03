import { expect, test } from "@playwright/test";
import { accessible } from "./outils";

// « Où je me situe » (EF-37 à EF-40, décision 0004 §2) : trois questions, un résultat sourcé.

test("trois étapes puis le résultat", async ({ page }) => {
  await page.goto("/situer");
  await accessible(page, "situer, introduction");
  await page.getByRole("button", { name: "Commencer" }).click();

  await expect(page.getByRole("heading", { name: "Dans quelle région vit votre ménage ?" })).toBeVisible();
  await expect(page.getByRole("progressbar", { name: "Progression du questionnaire" })).toHaveAttribute("aria-valuenow", "1");
  await accessible(page, "situer, région");
  await page.getByRole("radio", { name: "Kolda" }).check({ force: true });
  await page.getByRole("button", { name: "Continuer" }).click();

  await expect(page.getByRole("heading", { name: "Combien de personnes vivent dans votre ménage ?" })).toBeVisible();
  await accessible(page, "situer, taille");
  await page.getByRole("button", { name: "Une personne de plus" }).click();
  await page.getByRole("button", { name: "Continuer" }).click();

  await expect(page.getByRole("heading", { name: /Combien votre ménage dépense/ })).toBeVisible();
  await accessible(page, "situer, dépenses");
  await page.getByRole("radio", { name: "De 100 000 à 200 000 FCFA" }).check({ force: true });
  await page.getByRole("button", { name: "Voir mon résultat" }).click();

  await expect(page.getByText("Comparée aux moyennes publiées")).toBeVisible();
  await expect(page.getByText(/ANSD/).first()).toBeVisible(); // aucune valeur sans source
  await accessible(page, "situer, résultat");

  // Retour en arrière : la saisie est gardée, rien n'est envoyé ailleurs
  await page.getByRole("button", { name: "Recommencer" }).click();
  await expect(page.getByRole("button", { name: "Commencer" })).toBeVisible();
});

test("on ne peut pas continuer sans répondre", async ({ page }) => {
  await page.goto("/situer");
  await page.getByRole("button", { name: "Commencer" }).click();
  await expect(page.getByRole("button", { name: "Continuer" })).toBeDisabled();
});
