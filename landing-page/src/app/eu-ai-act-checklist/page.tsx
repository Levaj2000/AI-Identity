import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import JsonLd from "@/components/JsonLd";
import EUAIActChecklistContent from "./checklist-content";

export const metadata: Metadata = generatePageMetadata({
  title: "EU AI Act Compliance Checklist for AI Agents",
  description: "Free self-assessment for EU AI Act compliance. Check your AI agents against Articles 9, 11, 12, 14, and Annex III requirements before the August 2026 deadline.",
  path: "/eu-ai-act-checklist",
});

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "When does the EU AI Act take effect for high-risk AI systems?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "The EU AI Act's high-risk AI system requirements take full effect on August 2, 2026. This includes mandatory documentation, logging, human oversight, and risk management for AI agents operating in domains like hiring, finance, healthcare, and critical infrastructure.",
      },
    },
    {
      "@type": "Question",
      name: "What are the penalties for non-compliance with the EU AI Act?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Violations can result in fines of up to 35 million EUR or 7% of global annual turnover for prohibited practices, and up to 15 million EUR or 3% of turnover for other violations. These are GDPR-scale consequences applied to AI systems.",
      },
    },
    {
      "@type": "Question",
      name: "Do AI agents need their own identity under the EU AI Act?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. Articles 12 and 14 require traceability and human oversight of AI systems. This means every AI agent needs a unique, verifiable identity so its actions can be attributed, audited, and controlled individually — shared API keys across agents do not meet these requirements.",
      },
    },
    {
      "@type": "Question",
      name: "What logging requirements does the EU AI Act impose on AI agents?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Article 12 mandates automatic logging throughout the AI system lifecycle, including periods of use, input data that led to decisions, and identification of humans involved in verification. Logs must be complete, attributable to a specific AI system, retained appropriately, and accessible to authorities on request.",
      },
    },
    {
      "@type": "Question",
      name: "How do I know if my AI agent is high-risk under the EU AI Act?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "The Act classifies AI systems by use case under Annex III. High-risk categories include employment and worker management, credit scoring, healthcare diagnostics, critical infrastructure, education admissions, and law enforcement. Classification is based on what the agent does, not its architecture.",
      },
    },
    {
      "@type": "Question",
      name: "What is the fastest way to prepare AI agents for EU AI Act compliance?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Start by classifying each agent by risk tier, then implement per-agent identity with scoped permissions, set up tamper-proof audit logging, design human oversight controls, and establish continuous risk management. Tools like AI Identity can provide this infrastructure in a 15-minute integration.",
      },
    },
  ],
};

export default function EUAIActChecklistPage() {
  return (
    <>
      <JsonLd data={faqSchema} />
      <EUAIActChecklistContent />
    </>
  );
}
