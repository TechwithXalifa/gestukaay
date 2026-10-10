import type { Metadata } from "next";

export const metadata: Metadata = { title: "API publique" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
