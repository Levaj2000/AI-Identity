import type { Metadata } from "next";
import "../framer/styles.css";
import "./globals.css";

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
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[rgb(4,7,13)] text-[rgb(213,219,230)]">
        {children}
      </body>
    </html>
  );
}
