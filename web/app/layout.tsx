import type { Metadata } from "next";
import { Bricolage_Grotesque, Space_Mono, Unbounded } from "next/font/google";
import "./globals.css";
import { EnregistrerSW } from "@/components/EnregistrerSW";
import { LangueProvider } from "@/i18n/langue";

// 7.6 : polices auto-hébergées (téléchargées au build, servies par le site), sous-ensembles
// latins, font-display: swap. latin-ext ne se charge que si un caractère en a besoin (ŋ en wolof).
// Design system v2 : Unbounded (titres, chiffre), Bricolage Grotesque (texte), Space Mono (sources).
// Les variables remplacent --font-display, --font-sans et --font-mono de tokens.css à partir de <body>.
const unbounded = Unbounded({ subsets: ["latin", "latin-ext"], display: "swap", variable: "--font-display" });
const bricolage = Bricolage_Grotesque({ subsets: ["latin", "latin-ext"], display: "swap", variable: "--font-sans" });
const spaceMono = Space_Mono({ subsets: ["latin", "latin-ext"], weight: ["400", "700"], display: "swap", variable: "--font-mono" });

const LANGUE_AVANT_REACT =
  "try{if(localStorage.getItem('gestukaay.langue')==='wo')document.documentElement.dataset.langue='wo'}catch(e){}";

export const viewport = { width: "device-width", initialScale: 1, themeColor: "#17110b" };

export const metadata: Metadata = {
  title: { default: "Gëstukaay · le chiffre officiel du Sénégal", template: "%s · Gëstukaay" },
  description: "Le chiffre officiel, avec sa source et sa date.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // data-langue est posé avant le premier affichage (script ci-dessous) : un rechargement en WO ne
    // montre pas FR le temps que React démarre, ce qui peut durer quelques secondes en 3G.
    <html lang="fr" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: LANGUE_AVANT_REACT }} />
      </head>
      <body className={`${unbounded.variable} ${bricolage.variable} ${spaceMono.variable}`}>
        <LangueProvider>{children}</LangueProvider>
        <EnregistrerSW />
      </body>
    </html>
  );
}
