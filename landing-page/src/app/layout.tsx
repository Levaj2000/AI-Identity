import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import "@/framer/styles.css";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://www.ai-identity.co"),
  title: {
    default: "AI Identity — Identity Infrastructure for AI Agents",
    template: "%s | AI Identity",
  },
  description:
    "Per-agent API keys, scoped permissions, and tamper-proof audit trails for autonomous AI agents. Deploy in 15 minutes.",
  verification: {
    google: "ff7e4cc223c9fc7c",
  },
  robots: { index: true, follow: true },
  openGraph: {
    siteName: "AI Identity",
    type: "website",
    images: [{ url: "/images/og-image.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    site: "@AiIdentity",
    creator: "@AiIdentity",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-[rgb(4,7,13)] text-[rgb(213,219,230)]">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-[rgb(166,218,255)] focus:text-[rgb(4,7,13)] focus:rounded-lg focus:font-medium focus:text-sm"
        >
          Skip to main content
        </a>
        <Nav />
        <main id="main-content">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
