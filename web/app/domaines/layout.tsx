import type { Metadata } from "next";

export const metadata: Metadata = { title: "Domaines de données" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
