import type { Metadata } from "next";

export const metadata: Metadata = { title: "Où je me situe" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
