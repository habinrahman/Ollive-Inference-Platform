import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Ollive Chat",
  description: "Multi-turn inference client backed by Ollive telemetry."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
