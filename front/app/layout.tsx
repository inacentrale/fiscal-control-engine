import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "@/public/styles/globals.css";
import "@/public/styles/font.css";
import QueryProvider from "@/api/query-provider";

export const metadata: Metadata = {
  title: "Analyse Grand Livre",
  description: "Agent de revue fiscale pre-declaratif pour donnees comptables OHADA.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
