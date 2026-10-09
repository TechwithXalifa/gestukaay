import { expect, test } from "@playwright/test";
import { accessible, poser } from "./outils";

// Parcours P1 : une question, trois issues et seulement trois (contrat §3), sur le faux moteur.

test("accueil : question, exemples et domaines", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Posez votre question.");
  await expect(page.getByRole("textbox", { name: "Votre question" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Parcourir par domaine" })).toBeVisible();
  await expect(page.locator(".grille-domaines li")).toHaveCount(8); // deux lignes de quatre
  await accessible(page, "accueil");
});

test("pendant la recherche : le bouton tourne et les étapes viennent à l'écran", async ({ page }) => {
  // Retour de recette : rien ne bougeait là où l'on venait de cliquer, les étapes étaient plus bas
  await page.route("**/v1/ask", async (route) => {
    await new Promise((r) => setTimeout(r, 1500));
    await route.continue();
  });
  await page.goto("/");
  await page.getByRole("textbox", { name: "Votre question" }).fill("Combien d'habitants à Thiès ?");
  await page.getByRole("button", { name: "Envoyer la question" }).click();
  const bouton = page.getByRole("button", { name: "Recherche du chiffre officiel…" });
  await expect(bouton).toBeDisabled();
  await expect(bouton.locator(".spin")).toBeVisible();
  await expect(page.locator("[aria-busy=true]")).toBeInViewport();
  await expect(page).toHaveURL(/\/r\//);
});

test("réponse exacte : chiffre, source, graphique et tableau", async ({ page }) => {
  await poser(page, "Combien d'habitants à Thiès ?");
  await expect(page.getByText("Correspondance exacte")).toBeVisible();
  await expect(page.locator(".valeur")).toContainText("2 463 677");
  await expect(page.getByRole("complementary", { name: "Source officielle" })).toContainText("RGPH-5");
  await expect(page.getByRole("figure", { name: /Population des régions/ })).toBeVisible();
  await accessible(page, "réponse exacte");

  // Alternative texte du graphique (EF-28)
  await page.getByRole("button", { name: /Voir les 14 valeurs en tableau/ }).click();
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(15);
  await accessible(page, "réponse exacte, tableau");
});

test("classement : la zone demandée en grand, même si elle n'est pas en tête", async ({ page }) => {
  // Le moteur trie par valeur : Dakar est en tête, mais la question porte sur Thiès (mise en évidence)
  await poser(page, "Où se classe Thiès pour la population en 2023 ?");
  await expect(page.locator(".valeur")).toHaveCount(1);
  await expect(page.locator(".valeur")).toContainText(/2.463.677/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Thiès");
  await expect(page.getByText("Le classement complet des 2 zones")).toBeVisible();
  await accessible(page, "classement");
});

test("réponse approchée : aucun chiffre avant le choix, puis la valeur", async ({ page }) => {
  await poser(page, "Population de la ville de Thiès en 2023");
  await expect(page.getByText("Correspondance approchée")).toBeVisible();
  await expect(page.locator(".valeur")).toHaveCount(0); // EF-06 : rien n'est affiché avant le choix
  await accessible(page, "réponse approchée");

  await page.locator(".choix button").first().click();
  await expect(page.getByText("Correspondance exacte")).toBeVisible();
  await expect(page.locator(".valeur")).toBeVisible();
});

test("refus : message honnête et indicateurs proches qui se posent en un clic", async ({ page }) => {
  await poser(page, "Combien de personnes parlent sérère au Sénégal ?");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("n'existe pas");
  const suggestions = page.locator(".suggestions button");
  await expect(suggestions).toHaveCount(3);
  await accessible(page, "refus");

  await suggestions.first().click();
  await expect(page).toHaveURL(/\/r\/[\w-]+$/);
});

test("refus : suggérer l'indicateur manquant à l'équipe (EF-51)", async ({ page }) => {
  await poser(page, "Combien de personnes parlent sérère au Sénégal ?");
  await page.getByRole("button", { name: "Suggérer cet indicateur à l'équipe" }).click();
  await expect(page.getByRole("status").filter({ hasText: "votre suggestion est transmise" })).toBeVisible();
});

test("projection : badge et base, jamais présentée comme observée", async ({ page }) => {
  await poser(page, "Espérance de vie au Sénégal en 2035");
  await expect(page.locator(".badge.projection")).toHaveText("Projection");
  // \s : espace insécable devant « : » (typographie française, lib/typo.ts)
  await expect(page.getByText(/Ce n'est pas une valeur observée\.\sBase\s:/)).toBeVisible();
  await accessible(page, "projection");
});

test("comparaison : deux valeurs, deux barres", async ({ page }) => {
  await poser(page, "Population de Dakar et de Thiès en 2023");
  await expect(page.locator(".valeur")).toHaveCount(2);
  await expect(page.locator(".barre")).toHaveCount(2);
  // Un seul titre de niveau 1 : le second résultat est un titre de niveau 2 (WCAG 1.3.1)
  await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
  await expect(page.locator("h2.libelle")).toHaveCount(1);
});

test("exports PDF et CSV, adresse stable et vote", async ({ page, request }) => {
  await poser(page, "Combien d'habitants à Thiès ?");
  const id = page.url().split("/r/")[1];

  const csv = await request.get(await page.getByRole("link", { name: "Exporter CSV" }).getAttribute("href") ?? "");
  expect(csv.ok()).toBeTruthy();
  expect(csv.headers()["content-type"]).toContain("text/csv");
  expect(await csv.text()).toContain("Population totale;Thiès;SN-TH;2023;2463677");

  const pdf = await request.get(await page.getByRole("link", { name: "Exporter PDF" }).getAttribute("href") ?? "");
  expect(pdf.ok()).toBeTruthy();
  expect((await pdf.body()).subarray(0, 4).toString()).toBe("%PDF");

  // EF-29 : l'adresse se rouvre telle quelle
  await page.goto(`/r/${id}`);
  await expect(page.locator(".valeur")).toContainText("2 463 677");

  await page.getByRole("button", { name: "Oui" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Merci" })).toBeVisible();
});

test("signaler une erreur", async ({ page }) => {
  await poser(page, "Combien d'habitants à Thiès ?");
  await page.getByRole("button", { name: "Signaler une erreur" }).click();
  await expect(page.getByRole("group", { name: "Qu'est-ce qui ne va pas ?" })).toBeVisible();
  await accessible(page, "signalement");
  await page.getByRole("radio", { name: "Ce n'est pas la bonne zone" }).check();
  await page.getByRole("button", { name: "Envoyer le signalement" }).click();
  await expect(page.getByText("Merci, votre retour a été transmis")).toBeVisible();
});

test("au clavier seul : de l'accueil à la réponse", async ({ page, isMobile }) => {
  test.skip(isMobile, "parcours clavier : poste de bureau");
  await page.goto("/");
  const champ = page.getByRole("textbox", { name: "Votre question" });
  for (let i = 0; i < 15 && !(await champ.evaluate((e) => e === document.activeElement)); i++) {
    await page.keyboard.press("Tab");
  }
  await expect(champ).toBeFocused();
  await page.keyboard.type("Combien d'habitants à Thiès ?");
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/r\/[\w-]+$/);
  await expect(page.locator(".valeur")).toContainText("2 463 677");
});

test("adresse inconnue : message clair, pas d'erreur technique", async ({ page }) => {
  await page.goto("/r/inexistante");
  await expect(page.getByText("Cette réponse n'existe plus.")).toBeVisible();
  await accessible(page, "réponse introuvable");
});

test("suivi : les questions d'un même onglet partagent une conversation (décision 0021)", async ({ page }) => {
  const ids: (string | undefined)[] = [];
  page.on("request", (r) => {
    if (r.url().endsWith("/v1/ask") && r.method() === "POST") ids.push(r.postDataJSON().conversation_id);
  });
  await poser(page, "Combien d'habitants à Thiès ?");
  await page.getByRole("textbox", { name: "Votre question" }).fill("Et pour Kaolack ?");
  await page.getByRole("button", { name: "Envoyer la question" }).click();
  await expect.poll(() => ids.length).toBe(2);
  expect(ids[0]).toBeTruthy();
  expect(ids[1]).toBe(ids[0]);
});

test("vote : on peut encore signaler après un « Oui », et « Non » ouvre le signalement", async ({ page }) => {
  await poser(page, "Combien d'habitants à Thiès ?");
  await page.getByRole("button", { name: "Oui" }).click();
  await expect(page.getByRole("status").filter({ hasText: "votre retour a été transmis" })).toBeVisible();
  await page.getByRole("button", { name: "Signaler une erreur" }).click();
  await expect(page.getByRole("group", { name: "Qu'est-ce qui ne va pas ?" })).toBeVisible();
  await poser(page, "Combien d'habitants à Thiès ?");
  await page.getByRole("button", { name: "Non" }).click();
  await expect(page.getByRole("group", { name: "Qu'est-ce qui ne va pas ?" })).toBeVisible();
});
