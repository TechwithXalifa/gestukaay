import { expect, test } from "@playwright/test";
import { accessible } from "./outils";

// Widget à intégrer : un chiffre officiel toujours à jour dans le cadre d'un autre site (faux moteur : taux de
// pauvreté du Sénégal, de Dakar et de Kolda).

test("widget : dernière valeur, source, lien, et seule page autorisée en cadre", async ({ page, request }) => {
  const r = await request.get("/integrer/jcvcajc.taux-de-pauvrete?zone=SN-KD");
  expect(r.headers()["x-frame-options"]).toBeUndefined();
  expect(r.headers()["content-security-policy"]).toContain("frame-ancestors *");
  // Toutes les autres pages restent interdites en cadre
  expect((await request.get("/")).headers()["x-frame-options"]).toBe("DENY");

  await page.goto("/integrer/jcvcajc.taux-de-pauvrete?zone=SN-KD");
  await expect(page.locator(".widget-titre")).toHaveText("Taux de pauvreté · Kolda");
  await expect(page.locator(".widget-valeur")).toContainText("62,5");
  await expect(page.locator(".widget-source")).toContainText("2022");
  await expect(page.locator(".widget-source")).toContainText("EHCVM");
  await expect(page.getByRole("link", { name: /Gëstukaay/ })).toHaveAttribute("href", "/explorer?indicateur=jcvcajc.taux-de-pauvrete&zones=SN%2CSN-KD");
  await expect(page.getByRole("link", { name: /Gëstukaay/ })).toHaveAttribute("target", "_blank");
  await accessible(page, "widget");

  await page.goto("/integrer/inconnu?zone=SN");
  await expect(page.locator(".widget-titre")).toHaveText("Chiffre indisponible");
});

test("fiche indicateur : « Intégrer à un site » donne le code et l'aperçu", async ({ page }) => {
  await page.goto("/indicateurs/jcvcajc.taux-de-pauvrete");
  await page.getByRole("button", { name: "Intégrer à un site" }).click();
  const code = page.getByLabel("Code à copier");
  await expect(code).toHaveValue(/<iframe src="http:\/\/localhost:3000\/integrer\/jcvcajc\.taux-de-pauvrete\?zone=SN"/);
  await page.locator(".integrer").getByLabel("Zone", { exact: true }).selectOption("SN-KD");
  await page.getByLabel("Apparence").selectOption("sombre");
  await expect(code).toHaveValue(/zone=SN-KD&theme=sombre/);
  await expect(page.frameLocator("iframe[title^='Aperçu du widget']").locator(".widget-valeur")).toContainText("62,5");
  await accessible(page, "fiche, intégrer");
});
