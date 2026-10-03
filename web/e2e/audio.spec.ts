import { expect, test } from "@playwright/test";
import { accessible, poser } from "./outils";

// Réponse lue (EF-16). Le faux moteur renvoie une audio_url pour la question en wolof ;
// le test sert lui-même un court fichier audio à cette adresse.

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

test("réponse en wolof : le lecteur affiche la durée et se met en lecture", async ({ page }) => {
  await page.route("**/audio/**", (r) => r.fulfill({ contentType: "audio/wav", body: wav(3) }));
  await poser(page, "Ñaata nit ñoo dëkk Tiés ?");
  const bouton = page.getByRole("button", { name: /Écouter la réponse en wolof, 3 secondes/ });
  await expect(bouton).toBeVisible();
  await expect(page.getByText("0:03 · réponse lue")).toBeVisible();
  await accessible(page, "réponse avec audio");
  await bouton.click();
  await expect(page.getByRole("button", { name: "Mettre la lecture en pause" })).toBeVisible();
});

test("audio introuvable : le lecteur disparaît, le texte reste", async ({ page }) => {
  await page.route("**/audio/**", (r) => r.fulfill({ status: 404 }));
  await poser(page, "Ñaata nit ñoo dëkk Tiés ?");
  await expect(page.locator(".valeur")).toBeVisible();
  await expect(page.locator(".lecteur-audio")).toHaveCount(0);
});

test("pas d'audio demandé : pas de lecteur", async ({ page }) => {
  await poser(page, "Combien d'habitants à Thiès ?");
  await expect(page.locator(".valeur")).toBeVisible();
  await expect(page.locator(".lecteur-audio")).toHaveCount(0);
});
