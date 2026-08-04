import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import JsonLd from "@/components/JsonLd";
import SpecContent from "./spec-content";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Forensics Specification — Shipped in OCSF 1.9.0",
  description:
    "The AI Forensics Audit Trail Specification v1.0 — the open draft that graduated upstream. Its core primitives, the attestation object and record_integrity profile, shipped in OCSF 1.9.0. The OCSF schema is the normative home; the AI Identity platform is the production reference implementation.",
  path: "/spec",
});

const techArticleSchema = {
  "@context": "https://schema.org",
  "@type": "TechArticle",
  headline: "AI Forensics Audit Trail Specification v1.0",
  description:
    "Open reference draft for forensic audit trails of autonomous AI agents. Graduated upstream: the attestation object and record_integrity profile shipped in OCSF 1.9.0.",
  author: { "@type": "Organization", name: "AI Identity" },
  publisher: { "@type": "Organization", name: "AI Identity" },
  datePublished: "2026-05-15",
  dateModified: "2026-08-04",
  creativeWorkStatus: "Archived — superseded by OCSF 1.9.0",
  inLanguage: "en",
  proficiencyLevel: "Expert",
  dependencies: "OCSF; OpenTelemetry GenAI semconv; SPIFFE/SPIRE; DSSE",
};

export default function SpecPage() {
  return (
    <>
      <JsonLd data={techArticleSchema} />
      <SpecContent />
    </>
  );
}
