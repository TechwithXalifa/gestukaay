import { expect, test } from "@playwright/test";
import { accessible, poser } from "./outils";

// Réponse en français lue par la voix de l'appareil (Web Speech). Le navigateur des tests n'a pas de voix :
// une fausse synthèse, installée avant la page, garde ce qui serait dit.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const dit: string[] = [];
    (window as unknown as { __dit: string[] }).__dit = dit;
    class Enonce { text: string; voice: unknown = null; lang = ""; rate = 1; onend: (() => void) | null = null; onerror: (() => void) | null = null;
      constructor(t: string) { this.text = t; } }
    Object.defineProperty(window, "SpeechSynthesisUtterance", { value: Enonce });
    Object.defineProperty(window, "speechSynthesis", {
      value: {
        getVoices: () => [{ name: "Voix de test", lang: "fr-FR", localService: true }],
        speak: (u: Enonce) => dit.push(u.text),
        cancel: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
      },
    });
  });
});

test("écouter une réponse en français : la voix de l'appareil, les milliers lus comme un nombre", async ({ page }) => {
  await poser(page, "Combien d'habitants à Thiès ?");
  const ecouter = page.getByRole("button", { name: "Écouter la réponse, lue par la voix de votre appareil" });
  await expect(ecouter).toBeVisible();
  await accessible(page, "lecture en français");
  await ecouter.click();
  await expect(page.getByRole("button", { name: "Arrêter la lecture" })).toBeVisible();
  const dit = await page.evaluate(() => (window as unknown as { __dit: string[] }).__dit);
  expect(dit).toHaveLength(1);
  expect(dit[0]).toContain("2463677"); // pas « 2 463 677 » lu chiffre par chiffre
  await page.getByRole("button", { name: "Arrêter la lecture" }).click();
  await expect(ecouter).toBeVisible();
});

test("pas de voix française sur l'appareil : pas de bouton", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window.speechSynthesis, "getVoices", { value: () => [{ name: "English", lang: "en-US", localService: true }] });
  });
  await poser(page, "Combien d'habitants à Thiès ?");
  await expect(page.locator(".valeur")).toBeVisible();
  await expect(page.getByRole("button", { name: /voix de votre appareil/ })).toHaveCount(0);
});
