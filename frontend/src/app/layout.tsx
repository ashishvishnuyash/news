import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Republic Bulletin",
  description: "A black and white retro newspaper portal built with Next.js and FastAPI.",
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
      <body>{children}</body>
    </html>
  );
}
