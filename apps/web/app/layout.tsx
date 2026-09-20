import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Orrery",
  description: "A study platform you navigate as a knowledge map.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
