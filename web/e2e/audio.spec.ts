import { expect, test } from "@playwright/test";
import { accessible, poser, poserAVoix } from "./outils";

// Réponse lue (EF-16, décision 0040) : une question posée à la voix en wolof reçoit l'adresse de sa note
// (`/v1/answers/{id}/audio.ogg`, calculée à la demande par l'API) ; le test sert lui-même un court audio.

/** WAV PCM 8 kHz mono, `secondes` de silence. */
function wav(secondes: number): Buffer {
  const n = 8000 * secondes;
  const b = Buffer.alloc(44 + n * 2);
  b.write("RIFF", 0); b.writeUInt32LE(36 + n * 2, 4); b.write("WAVE", 8);
  b.write("fmt ", 12); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22);
  b.writeUInt32LE(8000, 24); b.writeUInt32LE(16000, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34);
  b.write("data", 36); b.writeUInt32LE(n * 2, 40);
  return b;
}

const servirAudio = (page: import("@playwright/test").Page, secondes = 3) =>
  page.route("**/audio.ogg", (r) => r.fulfill({ contentType: "audio/wav", body: wav(secondes) }));

test("ordinateur : question vocale en wolof, bouton « Écouter », rien ne démarre seul", async ({ page, isMobile }) => {
  test.skip(isMobile, "sur téléphone, la note démarre seule (test suivant)");
  await servirAudio(page);
  await poserAVoix(page, "Ñaata nit ñoo dëkk Tiés ?");
  const bouton = page.getByRole("button", { name: /Écouter la réponse en wolof, 3 secondes/ });
  await expect(bouton).toBeVisible();
  await expect(page.getByText("0:03 · réponse lue")).toBeVisible();
  await page.waitForTimeout(500);
  await expect(bouton).toBeVisible(); // toujours pas en lecture
  await accessible(page, "réponse avec audio");
  await bouton.click();
  await expect(page.getByRole("button", { name: "Mettre la lecture en pause" })).toBeVisible();
});

test("téléphone : la note démarre seule après une question vocale, pas en rouvrant le lien", async ({ page, isMobile }) => {
  test.skip(!isMobile, "lecture automatique : écran tactile seulement");
  await servirAudio(page, 5);
  await poserAVoix(page, "Ñaata nit ñoo dëkk Tiés ?");
  await expect(page.getByRole("button", { name: "Mettre la lecture en pause" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", { name: /Écouter la réponse en wolof/ })).toBeVisible();
  await page.waitForTimeout(500);
  await expect(page.getByRole("button", { name: "Mettre la lecture en pause" })).toHaveCount(0);
});

test("audio introuvable : le lecteur disparaît, le texte reste", async ({ page }) => {
  await page.route("**/audio.ogg", (r) => r.fulfill({ status: 404 }));
  await poserAVoix(page, "Ñaata nit ñoo dëkk Tiés ?");
  await expect(page.locator(".valeur")).toBeVisible();
  await expect(page.locator(".lecteur-audio")).toHaveCount(0);
});

test("question écrite en wolof, ou vocale en français : pas de lecteur", async ({ page }) => {
  await poser(page, "Ñaata nit ñoo dëkk Tiés ?");
  await expect(page.locator(".valeur")).toBeVisible();
  await expect(page.locator(".lecteur-audio")).toHaveCount(0);
  await poserAVoix(page, "Combien d'habitants à Thiès ?");
  await expect(page.locator(".valeur")).toBeVisible();
  await expect(page.locator(".lecteur-audio")).toHaveCount(0);
});
