import { defineConfig, devices } from "@playwright/test";

/**
 * Parcours du site de bout en bout (recette P1 à P4) et accessibilité (axe-core).
 * Lance l'API sur le faux moteur et le site déjà construit (`npm run build` d'abord) :
 *
 *     npm run build && npm run test:e2e
 */
// Compte du back-office des tests, créé au lancement de l'API dans une base jetable (décision 0037)
export const COMPTE_ADMIN = { identifiant: "e2e", motDePasse: "mot-de-passe-des-tests-e2e" };

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  // En local, 2 à la fois : au-delà, un poste chargé fait dépasser les délais (faux échecs)
  workers: process.env.CI ? undefined : 2,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://localhost:3000",
    locale: "fr-FR",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "bureau",
      use: {
        ...devices["Desktop Chrome"],
        // Faux micro : la fenêtre « Je vous écoute » s'ouvre sans matériel ni question d'autorisation
        launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] },
        permissions: ["microphone"],
      },
    },
    // Appareil de référence du cahier (7.6) : petit écran Android
    { name: "mobile", use: { ...devices["Galaxy S9+"], viewport: { width: 360, height: 640 } } },
  ],
  webServer: [
    {
      command:
        "rm -f .base-e2e.db && printf '%s\\n' \"$MOT_DE_PASSE\" | uv run python -m gestukaay_backend.comptes creer e2e" +
        " && uv run python -m uvicorn gestukaay_backend.app:app --port 8000",
      cwd: "..",
      url: "http://localhost:8000/health",
      // Limites de requêtes coupées : les tests posent des dizaines de questions par minute
      env: {
        GESTUKAAY_MOTEUR: "fake",
        GESTUKAAY_BASE: "sqlite:///.base-e2e.db",
        MOT_DE_PASSE: COMPTE_ADMIN.motDePasse,
        GESTUKAAY_LIMITES: "off",
        PYTHONUTF8: "1",
      },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm start",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
