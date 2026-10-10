import type { Metadata } from "next";

export const metadata: Metadata = { title: "Mes chiffres" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
