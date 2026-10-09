import { expect, test } from "@playwright/test";
import { poser, poserAVoix } from "./outils";

test("en-têtes de sécurité du site", async ({ page }) => {
  const r = await page.goto("/");
  const h = r!.headers();
  expect(h["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(h["x-content-type-options"]).toBe("nosniff");
  expect(h["permissions-policy"]).toContain("microphone=(self)");
  expect(h["x-powered-by"]).toBeUndefined();
});

test("aucune violation de la politique de contenu sur les parcours", async ({ page }) => {
  const violations: string[] = [];
  page.on("console", (m) => {
    if (/Content Security Policy|Refused to/i.test(m.text())) violations.push(m.text());
  });
  await page.route("**/audio.ogg", (r) => r.fulfill({ status: 404 }));
  await poser(page, "Combien d'habitants à Thiès ?"); // graphique, exports
  await poserAVoix(page, "Ñaata nit ñoo dëkk Tiés ?"); // lecteur audio
  await page.goto("/situer");
  await page.goto("/methode");
  expect(violations).toEqual([]);
});
