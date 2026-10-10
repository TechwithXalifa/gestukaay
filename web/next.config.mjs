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

const COMMUNS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // Le micro pour le site lui-même seulement ; ni caméra ni position
  { key: "Permissions-Policy", value: "microphone=(self), camera=(), geolocation=(), payment=()" },
];
const ENTETES = [
  ...COMMUNS,
  { key: "X-Frame-Options", value: "DENY" },
  ...(process.env.NODE_ENV === "production" ? [{ key: "Content-Security-Policy", value: CSP }] : []),
];
// Widget à intégrer (/integrer/…) : la seule page qu'un autre site peut afficher dans un cadre. Ni micro ni
// formulaire : un chiffre, sa source et un lien qui s'ouvre dans un nouvel onglet.
const ENTETES_WIDGET = [
  ...COMMUNS,
  ...(process.env.NODE_ENV === "production"
    ? [{ key: "Content-Security-Policy", value: CSP.replace("frame-ancestors 'none'", "frame-ancestors *") }]
    : []),
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
    return [
      { source: "/((?!integrer/).*)", headers: ENTETES },
      { source: "/integrer/:chemin*", headers: ENTETES_WIDGET },
    ];
  },
};

export default nextConfig;
