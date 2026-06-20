import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import JsonLd from "@/components/JsonLd";
import ComplianceContent from "./compliance-pack-content";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Forensics Compliance Pack — NYDFS, SEC 17a-4, MiFID II",
  description: "Pre-built AI agent forensics profiles for financial services. NYDFS 23 NYCRR 500, SEC Rule 17a-4 retention, MiFID II audit. Tamper-evident hash-chained evidence, DSSE-signed attestations, one-click examiner-ready export.",
  path: "/industries/finance/compliance-pack",
});

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "How do AI agents comply with NYDFS 23 NYCRR 500?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "NYDFS 23 NYCRR 500 requires access controls, audit trails, multi-factor authentication for privileged access, and third-party service provider risk assessments. AI agents must have per-agent cryptographic identity (not shared API keys), scoped credentials that can be revoked individually, and tamper-evident audit logs attributable to a specific agent. The §500.11 third-party assessment evidence packet should map each AI agent's permissions and audit trail directly to the rule's required controls.",
      },
    },
    {
      "@type": "Question",
      name: "Are AI agent decisions subject to SEC Rule 17a-4 records retention?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. SEC Rule 17a-4 imposes WORM-equivalent records retention on broker-dealer business records, which includes AI-assisted advisory, trading, and execution decisions. Compliant retention requires tamper-evident hash-chained audit logs, decision-by-decision attribution to a named agent identity, and a 6+ year retention horizon. Long retention windows are why the signing path is crypto-agile — the signature algorithm is pluggable, so signatures applied today stay verifiable as cryptographic standards evolve over the retention window.",
      },
    },
    {
      "@type": "Question",
      name: "How does MiFID II Article 16 record-keeping apply to AI agents?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "MiFID II Article 16 requires record-keeping for advisory and execution decisions, including timestamped order-handling evidence and reconstructable decision trails. When AI agents participate in advisory or execution, the same record-keeping obligations apply: every decision needs an attributable identity, a precise timestamp, the policy that was evaluated, and a tamper-evident trail that supports ESMA-style transaction reporting.",
      },
    },
    {
      "@type": "Question",
      name: "Why do shared API keys fail financial services compliance for AI agents?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Shared API keys across AI agents fail compliance for one core reason: examiners cannot answer 'which agent made this decision.' Without per-agent identity, attribution is impossible, scoped revocation is impossible, and the audit trail cannot establish least-privilege. NYDFS, SEC, and MiFID all require attributable access controls. Per-agent cryptographic credentials are the minimum bar.",
      },
    },
    {
      "@type": "Question",
      name: "What's in the AI Identity Financial Services Compliance Pack?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "The Compliance Pack ships three pre-built profiles — NYDFS 23 NYCRR 500, SEC Rule 17a-4, and MiFID II — plus per-agent cryptographic credentials scoped to fund/desk/strategy, a tamper-evident audit chain mapped to each regulator's evidence schema, one-click compliance export bundles (PDF + JSON) for examiner requests, control cross-walks to SOC 2 CC6/CC7 and ISO 27001 A.12/A.13, Cloud KMS HSM signing, and real-time SIEM push via signed webhook.",
      },
    },
    {
      "@type": "Question",
      name: "How long does an AI agent compliance pack take to deploy?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "The pre-built compliance profiles are configuration, not custom integration work. A typical financial services design partner deployment is 15–30 minutes for the SDK integration, plus the time to map your existing AI agents to the appropriate profile (NYDFS, SEC 17a-4, MiFID II, or combinations). Once configured, every agent decision is automatically attributable, signed, and exportable in the format your examiners expect.",
      },
    },
  ],
};

export default function FinanceCompliancePackPage() {
  return (
    <>
      <JsonLd data={faqSchema} />
      <ComplianceContent />
    </>
  );
}
