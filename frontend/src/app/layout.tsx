import type { Metadata } from "next";
import { SITE_BASE_URL } from "../lib/config";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_BASE_URL || "http://localhost:3000"),
  applicationName: "The Republic Bulletin",
  title: {
    default: "The Republic Bulletin",
    template: "%s | The Republic Bulletin",
  },
  description: "Independent reporting, analysis, and public-interest journalism from The Republic Bulletin.",
  openGraph: {
    type: "website",
    siteName: "The Republic Bulletin",
    title: "The Republic Bulletin",
    description: "Independent reporting, analysis, and public-interest journalism.",
  },
  twitter: {
    card: "summary_large_image",
    title: "The Republic Bulletin",
    description: "Independent reporting, analysis, and public-interest journalism.",
  },
  icons: {
    icon: "/favicon.png",
    shortcut: "/favicon.png",
    apple: "/favicon.png",
  },
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body><a className="skip-link" href="#main-content">Skip to main content</a>{children}</body>
    </html>
  );
}
