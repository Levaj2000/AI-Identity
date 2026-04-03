import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import DocsContent from "./docs-content";

export const metadata: Metadata = generatePageMetadata({
  title: "Documentation — AI Identity API & SDK",
  description: "API reference, SDK guides, and integration documentation for AI Identity. Get started in 15 minutes with per-agent keys and audit trails.",
  path: "/docs",
});

export default function DocsPage() {
  return <DocsContent />;
}
