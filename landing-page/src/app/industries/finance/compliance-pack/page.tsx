import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import ComplianceContent from "./compliance-pack-content";

export const metadata: Metadata = generatePageMetadata({
  title: "Financial Services AI Compliance Pack — NYDFS, SEC 17a-4, MiFID II",
  description: "Pre-built AI agent compliance profiles for financial services. NYDFS 23 NYCRR 500, SEC Rule 17a-4 retention, MiFID II audit. One-click compliance evidence export, mapped to the controls your auditors already ask for.",
  path: "/industries/finance/compliance-pack",
});

export default function FinanceCompliancePackPage() {
  return <ComplianceContent />;
}
