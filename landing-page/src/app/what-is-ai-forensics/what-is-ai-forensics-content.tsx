import Link from "next/link";
import { pillars } from "@/data/pillars";

const triggers = [
  {
    label: "Regulatory review",
    body: "A regulator asks how an autonomous agent reached a decision that affected a customer, a payment, or a clinical outcome. The answer has to be reconstructable, not asserted.",
  },
  {
    label: "Incident response",
    body: "An agent took an action with material impact — a refund, a trade, a deletion, a contract acceptance. Root-cause analysis needs every step from authentication to action, with timing intact.",
  },
  {
    label: "Customer dispute",
    body: "A customer contests an action an agent took on their behalf. Evidence has to attribute the decision to a specific agent identity, policy state, and input context.",
  },
  {
    label: "Compliance demonstration",
    body: "EU AI Act, NIST AI RMF, SOC 2, HIPAA, and ISO 42001 increasingly require demonstrable decision traceability for AI systems. Periodic attestation is not enough — auditors want per-action records.",
  },
];

const runtimeVsForensics = [
  {
    runtime: "Prevent prompt injection in the moment",
    forensics: "Reconstruct which inputs the agent saw and how policy evaluated them",
  },
  {
    runtime: "Block a jailbreak attempt",
    forensics: "Produce evidence the block happened and the chain wasn't tampered with",
  },
  {
    runtime: "Rate-limit a misbehaving agent",
    forensics: "Attribute the misbehavior to a specific agent identity and policy state",
  },
  {
    runtime: "Detect anomalous tool calls",
    forensics: "Replay the tool-call sequence with cryptographic proof of order and content",
  },
];

export default function WhatIsAiForensicsContent() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-12 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="w-2 h-2 rounded-full bg-[rgb(166,218,255)]" />
            <span className="text-[rgb(166,218,255)] text-sm font-medium">
              Discipline Overview
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            What is{" "}
            <span className="text-[rgb(166,218,255)]">AI Forensics</span>?
          </h1>
          <p className="text-lg text-gray-300 max-w-[760px] mx-auto leading-relaxed">
            AI forensics is the discipline of reconstructing what an autonomous AI agent did, why, and on whose authority &mdash; with tamper-evident, cryptographically-signed evidence that an auditor can verify offline, with no dependency on the vendor that ran the agent.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/spec"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
            >
              Read the v1.0 reference specification
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </Link>
            <Link
              href="/forensics"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
            >
              See an implementation
            </Link>
          </div>
        </div>
      </section>

      {/* Why not runtime security */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[1000px] mx-auto">
          <div className="text-center mb-10">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-3">
              The Category Distinction
            </p>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
              Forensics is not runtime security
            </h2>
            <p className="text-sm text-gray-400 max-w-[640px] mx-auto">
              Runtime security tries to prevent bad agent behavior in the moment. Forensics assumes something will eventually go wrong and prepares the evidence to reconstruct it afterward. Both matter. They are different jobs.
            </p>
          </div>
          <div className="overflow-hidden rounded-2xl border border-[rgba(216,231,242,0.07)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-white/[0.05]">
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    AI Runtime Security
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    AI Forensics
                  </th>
                </tr>
              </thead>
              <tbody>
                {runtimeVsForensics.map((row, i) => (
                  <tr key={row.runtime} className={i % 2 === 0 ? "bg-white/[0.02]" : ""}>
                    <td className="px-6 py-4 text-gray-300">{row.runtime}</td>
                    <td className="px-6 py-4 text-gray-300">{row.forensics}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Four Pillars (discipline framing) */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[1000px] mx-auto">
          <div className="text-center mb-10">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-3">
              The Discipline
            </p>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
              Four questions every audit eventually asks
            </h2>
            <p className="text-sm text-gray-400 max-w-[620px] mx-auto">
              AI forensics organizes evidence around four questions. The first three are governance primitives; the fourth is what makes the discipline forensic rather than operational.
            </p>
          </div>
          <div className="overflow-hidden rounded-2xl border border-[rgba(216,231,242,0.07)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-white/[0.05]">
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    Pillar
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    The auditor&apos;s question
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    Evidence required
                  </th>
                </tr>
              </thead>
              <tbody>
                {pillars.map((p, i) => (
                  <tr
                    key={p.pillar}
                    className={`${i % 2 === 0 ? "bg-white/[0.02]" : ""} ${p.pillar === "Forensics" ? "border-l-2 border-l-[rgb(166,218,255)]" : ""}`}
                  >
                    <td className="px-6 py-4 font-semibold text-white whitespace-nowrap">{p.pillar}</td>
                    <td className="px-6 py-4 text-gray-400 italic">{p.question}</td>
                    <td className="px-6 py-4 text-gray-300">{p.capability}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* When you need it */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[1000px] mx-auto">
          <div className="text-center mb-10">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-3">
              Trigger Events
            </p>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
              When AI forensics is the right tool
            </h2>
            <p className="text-sm text-gray-400 max-w-[620px] mx-auto">
              You don&apos;t need forensics to deploy an agent. You need it the first time someone asks for an account of what an agent did and a screenshot of the dashboard isn&apos;t enough.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {triggers.map((t) => (
              <div
                key={t.label}
                className="p-5 rounded-2xl border border-[rgba(216,231,242,0.07)] bg-white/[0.02]"
              >
                <h3 className="text-base font-semibold text-white mb-2">{t.label}</h3>
                <p className="text-sm text-[rgba(213,219,230,0.7)] leading-relaxed">{t.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Reference standard pointer */}
      <section className="py-20 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[800px] mx-auto text-center">
          <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-3">
            The Open Reference
          </p>
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
            There&apos;s a draft specification for this
          </h2>
          <p className="text-sm text-[rgba(213,219,230,0.7)] mb-8 max-w-[600px] mx-auto leading-relaxed">
            The <strong className="text-white">AI Forensics Audit Trail Specification v1.0</strong> is an open reference standard for tamper-evident, cryptographically-signed audit trails of autonomous AI agents. It profiles OCSF, OpenTelemetry GenAI semconv, MITRE ATLAS, SPIFFE, and NIST AI RMF rather than inventing a competing schema. Published under CC-BY-4.0.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link
              href="/spec"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
            >
              Read the v1.0 specification
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </Link>
            <Link
              href="/forensics"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
            >
              See how AI Identity implements it
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
