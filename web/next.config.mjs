/** @type {import('next').NextConfig} */
const nextConfig = {
  // Les types du contrat vivent hors de web/ (../contracts/generated)
  experimental: { externalDir: true },
};

export default nextConfig;
