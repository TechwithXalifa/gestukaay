import type { Metadata } from "next";

/** Back-office : jamais indexé. */
export const metadata: Metadata = { title: "Back-office", robots: { index: false, follow: false } };

export default function LayoutAdmin({ children }: { children: React.ReactNode }) {
  return children;
}
