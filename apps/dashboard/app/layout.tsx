import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Ollive Observability",
  description: "Operational dashboard for LLM inference telemetry."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
