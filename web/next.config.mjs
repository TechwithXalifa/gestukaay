import path from "node:path";
import { fileURLToPath } from "node:url";

const racine = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const API = new URL(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").origin;

// Politique de contenu : nos scripts, notre API, l'audio des réponses ; rien d'autre.
// 'unsafe-inline' pour les scripts : Next insère ses données de page en ligne (pas de nonce
// sans rendu dynamique de toutes les pages). Le mode dev a besoin d'eval : CSP en production seulement.
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self' ${API}`,
  `media-src 'self' blob: ${API} https:`, // audio de la réponse, servi par l'API ou un stockage https
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const ENTETES = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  // Le micro pour le site lui-même seulement ; ni caméra ni position
  { key: "Permissions-Policy", value: "microphone=(self), camera=(), geolocation=(), payment=()" },
  ...(process.env.NODE_ENV === "production" ? [{ key: "Content-Security-Policy", value: CSP }] : []),
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Serveur autonome pour l'image Docker (web/Dockerfile)
  output: "standalone",
  // Les types du contrat vivent hors de web/ (../contracts/generated)
  outputFileTracingRoot: racine,
  experimental: { externalDir: true },
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:chemin*", headers: ENTETES }];
  },
};

export default nextConfig;
