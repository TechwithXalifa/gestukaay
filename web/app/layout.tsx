import type { Metadata } from "next";
import { Lora, Poppins } from "next/font/google";
import "./globals.css";
import { EnregistrerSW } from "@/components/EnregistrerSW";
import { LangueProvider } from "@/i18n/langue";

// 7.6 : polices auto-hébergées (téléchargées au build, servies par le site), sous-ensembles
// latins, font-display: swap. latin-ext ne se charge que si un caractère en a besoin (ŋ en wolof).
// Les variables remplacent --font-sans et --font-serif de tokens.css à partir de <body>.
const poppins = Poppins({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-sans",
});
const lora = Lora({ subsets: ["latin", "latin-ext"], weight: ["400"], display: "swap", variable: "--font-serif" });

export const viewport = { width: "device-width", initialScale: 1, themeColor: "#1D4448" };

export const metadata: Metadata = {
  title: "Gëstukaay",
  description: "Le chiffre officiel, avec sa source et sa date.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className={`${poppins.variable} ${lora.variable}`}>
        <LangueProvider>{children}</LangueProvider>
        <EnregistrerSW />
      </body>
    </html>
  );
}
