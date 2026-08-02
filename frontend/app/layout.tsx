import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CB Nest — PeopleOps Copilot",
  description: "AI-powered HR operations copilot",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-base text-ink font-body antialiased">{children}</body>
    </html>
  );
}
