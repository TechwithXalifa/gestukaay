import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gëstukaay",
  description: "Le chiffre officiel, avec sa source et sa date.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
