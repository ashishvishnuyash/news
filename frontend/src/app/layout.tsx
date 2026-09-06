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
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;800;900&family=IBM+Plex+Mono:ital,wght@0,400;0,600;0,700;1,400&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;0,6..72,700;0,6..72,800;1,6..72,400;1,6..72,600&family=Playfair+Display:ital,wght@0,400;0,600;0,700;0,800;0,900;1,400;1,700;1,900&family=UnifrakturMaguntia&display=swap"
          rel="stylesheet"
        />
        <script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9253714889938600"
          crossOrigin="anonymous"
        />
      </head>
      <body><a className="skip-link" href="#main-content">Skip to main content</a>{children}</body>
    </html>
  );
}

