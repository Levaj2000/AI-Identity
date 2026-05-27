import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import JsonLd from "@/components/JsonLd";
import WhatIsAiForensicsContent from "./what-is-ai-forensics-content";

export const metadata: Metadata = generatePageMetadata({
  title: "What is AI Forensics? — Definition, Discipline, and Reference Spec",
  description:
    "AI forensics is the discipline of reconstructing what an autonomous AI agent did, why, and on whose authority — with cryptographic evidence that holds up in audit, regulatory review, and dispute. A discipline-neutral overview with links to the open v1.0 reference specification.",
  path: "/what-is-ai-forensics",
});

const definedTermSchema = {
  "@context": "https://schema.org",
  "@type": "DefinedTerm",
  name: "AI Forensics",
  description:
    "AI forensics is the discipline of reconstructing what an autonomous AI agent did, why, and on whose authority — with tamper-evident, cryptographically-signed evidence that an auditor can verify offline without trusting the vendor.",
  inDefinedTermSet: {
    "@type": "DefinedTermSet",
    name: "AI Forensics Audit Trail Specification v1.0",
    url: "https://www.ai-identity.co/spec",
  },
  termCode: "ai-forensics",
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "What is AI forensics?",
      acceptedAnswer: {
        "@type": "Answer",
        text:
          "AI forensics is the discipline of reconstructing what an autonomous AI agent did, why, and on whose authority. It produces tamper-evident, cryptographically-signed evidence of agent actions that an auditor can verify offline, with no dependency on the vendor that ran the agent.",
      },
    },
    {
      "@type": "Question",
      name: "How is AI forensics different from AI runtime security?",
      acceptedAnswer: {
        "@type": "Answer",
        text:
          "Runtime security tries to prevent bad agent behavior in the moment — prompt injection filters, jailbreak detectors, rate limits. Forensics assumes something will eventually go wrong and focuses on reconstructing the chain of evidence afterward: who authorized this agent, what policy applied, what it actually did, and whether the audit trail itself is intact.",
      },
    },
    {
      "@type": "Question",
      name: "When do you need AI forensics?",
      acceptedAnswer: {
        "@type": "Answer",
        text:
          "Typical triggers: a regulator or auditor asks how an autonomous agent reached a decision; an internal incident needs to be reconstructed for root-cause analysis; a customer disputes an action taken by an agent on their behalf; or a compliance regime (EU AI Act, NIST AI RMF, SOC 2, HIPAA) requires demonstrable decision traceability for AI systems.",
      },
    },
    {
      "@type": "Question",
      name: "Is there a standard for AI forensics?",
      acceptedAnswer: {
        "@type": "Answer",
        text:
          "The AI Forensics Audit Trail Specification v1.0 is an open reference standard that profiles existing standards — OCSF, OpenTelemetry GenAI, MITRE ATLAS, SPIFFE, NIST AI RMF, and the IETF Agent Identity Protocol draft — into a single coherent schema for forensic reconstruction. It is published under CC-BY-4.0.",
      },
    },
  ],
};

export default function WhatIsAiForensicsPage() {
  return (
    <>
      <JsonLd data={[definedTermSchema, faqSchema]} />
      <WhatIsAiForensicsContent />
    </>
  );
}
