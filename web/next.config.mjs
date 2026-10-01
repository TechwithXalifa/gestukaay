import path from "node:path";
import { fileURLToPath } from "node:url";

const racine = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Serveur autonome pour l'image Docker (web/Dockerfile)
  output: "standalone",
  // Les types du contrat vivent hors de web/ (../contracts/generated)
  outputFileTracingRoot: racine,
  experimental: { externalDir: true },
};

export default nextConfig;
