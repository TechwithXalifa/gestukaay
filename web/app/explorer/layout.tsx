import type { Metadata } from "next";

export const metadata: Metadata = { title: "Explorer et comparer" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
