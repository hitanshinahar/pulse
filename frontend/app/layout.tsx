import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pulse | Financial Recovery Platform",
  description:
    "Intelligent financial recovery and payment orchestration. Monitor obligations, decisions, and executions in real time.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full">{children}</body>
    </html>
  );
}
