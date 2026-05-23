import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import JsonLd from "@/components/JsonLd";
import SpecContent from "./spec-content";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Forensics Specification — Draft v1.0",
  description:
    "The AI Forensics Audit Trail Specification v1.0. An open reference standard for tamper-evident, cryptographically-signed audit trails of autonomous AI agents. Profiles OCSF, OpenTelemetry GenAI, MITRE ATLAS, SPIFFE, NIST AI RMF, and IETF AIP.",
  path: "/spec",
});

const techArticleSchema = {
  "@context": "https://schema.org",
  "@type": "TechArticle",
  headline: "AI Forensics Audit Trail Specification v1.0",
  description:
    "Open reference standard for forensic audit trails of autonomous AI agents.",
  author: { "@type": "Organization", name: "AI Identity" },
  publisher: { "@type": "Organization", name: "AI Identity" },
  datePublished: "2026-05-15",
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
