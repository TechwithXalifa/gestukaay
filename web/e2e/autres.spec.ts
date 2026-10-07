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

test("bascule FR/WO : le choix WO tient au rechargement, dès le premier affichage", async ({ page }) => {
  // Retour de recette : au rechargement, la page montrait FR le temps que React démarre
  await page.goto("/");
  await page.getByRole("button", { name: "WO", exact: true }).click();
  await page.route("**/_next/static/chunks/**", async (route) => {
    await new Promise((r) => setTimeout(r, 1500)); // React lent à démarrer, comme en 3G
    await route.continue();
  });
  await page.reload({ waitUntil: "commit" });
  await expect(page.locator("html")).toHaveAttribute("data-langue", "wo");
  const wo = page.getByRole("button", { name: "WO", exact: true });
  const fond = (b: typeof wo) => b.evaluate((e) => getComputedStyle(e).backgroundColor);
  expect(await fond(wo)).not.toBe(await fond(page.getByRole("button", { name: "FR", exact: true })));
  await expect(wo).toHaveAttribute("aria-pressed", "true"); // puis React confirme
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

test("pied de page : Méthode, À propos et Confidentialité", async ({ page }) => {
  for (const [lien, titre, h1] of [
    ["Méthode et transparence", "Méthode et transparence · Gëstukaay", "Comment Gëstukaay trouve vos chiffres"],
    ["À propos", "À propos · Gëstukaay", "Le chiffre officiel, avec sa source et sa date"],
    ["Confidentialité", "Confidentialité · Gëstukaay", "Ce que Gëstukaay garde, et ce qu'il ne garde pas"],
  ]) {
    await page.goto("/");
    await page.getByRole("navigation", { name: "Pied de page" }).getByRole("link", { name: lien }).click();
    await expect(page).toHaveTitle(titre);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(h1);
    await accessible(page, lien);
  }
});

test("tableau de bord : indicateurs, issues et questions non résolues (US-28)", async ({ page }) => {
  await poser(page, "Combien de personnes parlent sérère au Sénégal ?");
  await page.goto("/admin/tableau");
  await accessible(page, "tableau de bord, connexion");
  await page.getByLabel("Jeton d'administration").fill(JETON_ADMIN);
  await page.getByRole("button", { name: "Ouvrir le tableau de bord" }).click();
  await expect(page.getByRole("heading", { name: "Tableau de bord" })).toBeVisible();
  await expect(page.getByText("Questions traitées")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Issues du moteur" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Questions non résolues", exact: true })).toContainText("sérère");
  await page.getByRole("button", { name: "7 j" }).click();
  await expect(page.getByRole("button", { name: "7 j" })).toHaveAttribute("aria-pressed", "true");
  await accessible(page, "tableau de bord");

  await page.getByRole("link", { name: "Journal des requêtes" }).click();
  await expect(page.getByRole("heading", { name: "Journal des requêtes" })).toBeVisible(); // même jeton
});

test("barre latérale mobile : ouverture, navigation, fermeture (M-Menu)", async ({ page, isMobile }) => {
  test.skip(!isMobile, "la barre latérale remplace la navigation sous 768 px");
  await page.goto("/");
  const bouton = page.getByRole("button", { name: "Ouvrir le menu" });
  await bouton.click();
  const menu = page.getByRole("dialog", { name: "Menu" });
  await expect(menu).toBeVisible();
  await expect(menu.getByRole("link", { name: "Où je me situe" })).toBeVisible();
  await accessible(page, "barre latérale");

  await page.keyboard.press("Escape");
  await expect(menu).toBeHidden();
  await expect(bouton).toBeFocused();

  await bouton.click();
  await menu.getByRole("link", { name: "Où je me situe" }).click();
  await page.waitForURL(/\/situer$/);
  await expect(page.getByRole("dialog", { name: "Menu" })).toBeHidden();
});

test("méthode : résultats de la mesure publiés, réussites et erreurs (cahier 12.1)", async ({ page }) => {
  await page.goto("/methode");
  const mesure = page.getByRole("region", { name: "Ce que nous mesurons" });
  await expect(mesure).toContainText("89,2 %");
  await expect(mesure).toContainText("100 %");
  await expect(mesure).toContainText("1,4 s");
  await expect(mesure.getByText("objectif atteint", { exact: false })).toHaveCount(4);
  await expect(page.getByRole("region", { name: "Résultats par langue de la question" })).toContainText("pas encore mesuré");
  await expect(page.getByRole("region", { name: "Là où Gëstukaay se trompe encore" })).toContainText("5 questions");
  await accessible(page, "méthode, résultats");
});

test("jeu de test : écran du back-office, benchmark réservé au moteur réel (5.10)", async ({ page }) => {
  await page.goto("/admin/jeu-de-test");
  await page.getByLabel("Jeton d'administration").fill(JETON_ADMIN);
  await page.getByRole("button", { name: "Ouvrir le jeu de test" }).click();
  await expect(page.getByRole("heading", { name: "Jeu de test" })).toBeVisible();
  await expect(page.getByText(/\d+ questions de référence/)).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "faux moteur" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Relancer (règles locales)" })).toBeDisabled();
  await expect(page.getByRole("link", { name: "Jeu de test" })).toHaveAttribute("aria-current", "page");
  await accessible(page, "jeu de test");
});

test("adresse inconnue : page en français, avec l'en-tête et une suite (7.1 n° 7)", async ({ page }) => {
  const r = await page.goto("/cette-page-n-existe-pas");
  expect(r?.status()).toBe(404);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Cette page n'existe pas.");
  await expect(page.getByRole("link", { name: "Poser une question" }).last()).toHaveAttribute("href", "/");
  await accessible(page, "page introuvable");
});
