import { expect, test } from "@playwright/test";
import { accessible } from "./outils";

// Catalogue, fiche indicateur et Explorer (décision 0023), sur le faux moteur (exemples du contrat).

test("catalogue : liste, recherche dans l'adresse, lien vers la fiche", async ({ page }) => {
  await page.goto("/indicateurs");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Catalogue des indicateurs");
  await expect(page.getByRole("link", { name: /Taux de pauvreté/ })).toBeVisible();
  await accessible(page, "catalogue");

  await page.getByRole("searchbox", { name: "Rechercher un indicateur" }).fill("consommation");
  await page.getByRole("button", { name: "Rechercher" }).click();
  await expect(page).toHaveURL(/\?q=consommation$/);
  await expect(page.getByRole("link", { name: /Taux de pauvreté/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Consommation moyenne par tête/ })).toBeVisible();

  await page.goto("/indicateurs");
  await page.getByRole("link", { name: /Taux de pauvreté/ }).click();
  await expect(page).toHaveURL(/\/indicateurs\/jcvcajc\.taux-de-pauvrete$/);
});

test("fiche : définition citée, couverture, citation et accès à Explorer", async ({ page }) => {
  await page.goto("/indicateurs/jcvcajc.taux-de-pauvrete");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Taux de pauvreté");
  await expect(page.getByText("Incidence de la pauvreté")).toBeVisible();
  await expect(page.getByRole("region", { name: "Séries disponibles" })).toContainText("2011, 2019, 2022");
  await expect(page.getByRole("complementary", { name: "En bref" })).toContainText("EHCVM");
  await expect(page).toHaveTitle("Taux de pauvreté · Gëstukaay");
  await accessible(page, "fiche indicateur");

  await page.getByRole("link", { name: "Explorer et comparer" }).click();
  await expect(page).toHaveURL(/\/explorer\?indicateur=jcvcajc\.taux-de-pauvrete&zones=SN$/);
});

test("fiche : code inconnu, message clair", async ({ page }) => {
  await page.goto("/indicateurs/inconnu");
  await expect(page.getByRole("heading", { name: "Cet indicateur n'existe pas dans le catalogue." })).toBeVisible();
});

test("explorer : zones, période, absents, tableau et export, tout dans l'adresse", async ({ page }) => {
  await page.goto("/explorer?indicateur=jcvcajc.taux-de-pauvrete&zones=SN");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Taux de pauvreté");
  await expect(page.getByRole("figure")).toBeVisible();
  await accessible(page, "explorer");

  await page.getByLabel("Ajouter une zone").selectOption("SN-KD");
  await expect(page).toHaveURL(/zones=SN%2CSN-KD/);
  await page.getByLabel("Ajouter une zone").selectOption("SN-TH");
  await expect(page.getByRole("status").filter({ hasText: "Aucune donnée publiée" })).toContainText("Thiès");

  await page.getByLabel("De", { exact: true }).selectOption("2019");
  await page.getByRole("button", { name: "Tableau", exact: true }).click();
  await expect(page).toHaveURL(/debut=2019/);
  await expect(page).toHaveURL(/vue=tableau/);
  const tableau = page.getByRole("region", { name: "Taux de pauvreté" });
  await expect(tableau.getByRole("columnheader")).toHaveText(["Zone", "2019", "2022"]); // rien avant 2019
  await expect(tableau.getByRole("row", { name: /Kolda/ })).toContainText("62,5");
  await accessible(page, "explorer, tableau");

  const csv = page.getByRole("link", { name: "Exporter CSV" });
  await expect(csv).toHaveAttribute("href", /\/v1\/series\.csv\?indicateur=jcvcajc\.taux-de-pauvrete&zones=SN%2CSN-KD%2CSN-TH&debut=2019/);

  await page.getByRole("button", { name: "Retirer Thiès" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Aucune donnée publiée" })).toHaveCount(0);
});

test("explorer sans indicateur : on le choisit dans le catalogue", async ({ page }) => {
  await page.goto("/explorer");
  await page.getByRole("button", { name: /Taux de pauvreté/ }).click();
  await expect(page).toHaveURL(/indicateur=jcvcajc\.taux-de-pauvrete/);
  await expect(page.getByRole("figure")).toBeVisible();
});

test("fiche : suivre les mises à jour d'un indicateur par un flux Atom, sans donnée personnelle", async ({ page, request }) => {
  await page.goto("/indicateurs/jcvcajc.taux-de-pauvrete");
  await page.getByRole("button", { name: "Suivre les mises à jour" }).click();
  const adresse = page.getByLabel("Adresse du flux");
  await expect(adresse).toHaveValue("http://localhost:8000/v1/indicators/jcvcajc.taux-de-pauvrete/flux.atom?zone=SN");
  await page.getByLabel("Zone", { exact: true }).selectOption("SN-KD");
  await expect(adresse).toHaveValue(/zone=SN-KD$/);
  await accessible(page, "fiche, suivre");
  const flux = await request.get((await adresse.inputValue()) ?? "");
  expect(flux.headers()["content-type"]).toContain("application/atom+xml");
  expect(await flux.text()).toContain("<title>Taux de pauvreté · Kolda · 2022 : 62,5 %</title>");
});
