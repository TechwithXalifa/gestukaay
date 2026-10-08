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

  // Étape facultative (décision 0039) : on peut la passer, on choisit ici la campagne
  await expect(page.getByRole("heading", { name: /en ville ou à la campagne/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Passer cette question" })).toBeEnabled();
  await accessible(page, "situer, milieu");
  await page.getByRole("radio", { name: "À la campagne" }).check({ force: true });
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
  // v2 (0039) : seuil, milieu, graphique, groupes de bien-être, carte, « Et si… »
  await expect(page.getByText(/seuil de pauvreté/).first()).toBeVisible();
  await expect(page.getByText("Consommation moyenne par tête des ménages ruraux").first()).toBeVisible();
  await expect(page.getByRole("figure", { name: /Votre ménage et les repères publiés/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Comment se répartit la population/ })).toBeVisible();
  await expect(page.getByRole("group", { name: /Consommation moyenne par tête dans les 14 régions/ }).getByRole("button")).toHaveCount(14);
  await expect(page.getByRole("heading", { name: "Et si… ?" })).toBeVisible();
  await accessible(page, "situer, résultat");

  // le tableau remplace le graphique, sans perdre de repère
  await page.getByRole("button", { name: /valeurs en tableau/ }).click();
  await expect(page.getByRole("table")).toContainText("Votre ménage");

  // « Et si… » : un changement rappelle l'API, le résultat reste à l'écran
  await page.getByRole("combobox", { name: "Dépenses par mois" }).selectOption("200k_350k");
  await expect(page.getByText("Comparée aux moyennes publiées")).toBeVisible();

  // Retour en arrière : la saisie est gardée, rien n'est envoyé ailleurs
  await page.getByRole("button", { name: "Recommencer" }).click();
  await expect(page.getByRole("button", { name: "Commencer" })).toBeVisible();
});

test("on ne peut pas continuer sans répondre", async ({ page }) => {
  await page.goto("/situer");
  await page.getByRole("button", { name: "Commencer" }).click();
  await expect(page.getByRole("button", { name: "Continuer" })).toBeDisabled();
});

test("mobile : une région choisie amène « Continuer » au-dessus de la barre d'onglets", async ({ page, isMobile }) => {
  test.skip(!isMobile, "la barre d'onglets n'existe que sous 768 px");
  await page.goto("/situer");
  await page.getByRole("button", { name: "Commencer" }).click();
  await page.getByRole("radio", { name: "Kolda" }).check({ force: true });
  // C'est le site qui fait défiler (pas le clic de Playwright) : le bouton doit être visible et
  // rien ne doit le recouvrir (revue de la PR #155 : il s'arrêtait derrière la barre d'onglets)
  await expect
    .poll(() =>
      page.evaluate(() => {
        const bouton = document.querySelector<HTMLElement>(".continuer");
        const onglets = document.querySelector(".barre-onglets");
        if (!bouton || !onglets) return false;
        const r = bouton.getBoundingClientRect();
        const centre = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return r.top >= 0 && r.bottom <= onglets.getBoundingClientRect().top && !!centre && bouton.contains(centre);
      }),
    )
    .toBe(true);
});
