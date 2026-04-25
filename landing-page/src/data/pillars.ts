// Canonical source of truth for the Four Pillars of AI Agent Governance.
// All public-facing surfaces (home, product, forensics, etc.) MUST consume from
// this module. Order is fixed: Identity → Policy → Compliance → Forensics.
// See .claude/brand-voice-guidelines.md.

export type PillarName = "Identity" | "Policy" | "Compliance" | "Forensics";

export type Pillar = {
  pillar: PillarName;
  question: string;
  capability: string;
};

export const pillars: Pillar[] = [
  {
    pillar: "Identity",
    question: "Who is this agent?",
    capability: "Per-agent API keys, lifecycle management, scoped credentials.",
  },
  {
    pillar: "Policy",
    question: "What is it allowed to do?",
    capability: "Fail-closed gateway, deny-by-default policy evaluation.",
  },
  {
    pillar: "Compliance",
    question: "Can we prove rules were followed?",
    capability:
      "DSSE-signed session attestations, HMAC-verifiable audit logs, automated compliance assessments.",
  },
  {
    pillar: "Forensics",
    question: "What happened, provably?",
    capability:
      "Hash-chained logs, incident replay, export, offline cryptographic verification.",
  },
];

export const PILLARS_HEADING = "The Four Pillars of AI Agent Governance";
export const PILLARS_SUBHEADING =
  "Most solutions cover one or two. AI Identity covers all four.";
