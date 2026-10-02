import type { Metadata } from "next";
import "./globals.css";
import { EnregistrerSW } from "@/components/EnregistrerSW";

export const viewport = { width: "device-width", initialScale: 1, themeColor: "#1D4448" };

export const metadata: Metadata = {
  title: "Gëstukaay",
  description: "Le chiffre officiel, avec sa source et sa date.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Poppins:wght@400;500;600;700&display=swap"
        />
      </head>
      <body>
        {children}
        <EnregistrerSW />
      </body>
    </html>
  );
}
