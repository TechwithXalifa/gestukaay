import type { Metadata } from "next";

export const metadata: Metadata = { title: "À propos" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
