import type { Metadata } from "next";
import Link from "next/link";
import { generatePageMetadata } from "@/lib/metadata";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Agent Forensics — Replay Any Session, Prove Every Decision",
  description:
    "Replay any agent session step-by-step. Produce tamper-evident timelines regulators can verify independently of the vendor. HMAC-SHA256 hash-chained evidence for every agent action.",
  path: "/forensics",
});

const forensicFeatures = [
  {
    title: "Chain-of-Thought Capture",
    description:
      "Every gateway decision — ALLOW, DENY, policy match, upstream call — becomes an HMAC-chained entry tied to the specific agent, policy version, and credential used.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    title: "Incident Replay",
    description:
      "Given any agent and time window, reconstruct every request, every policy evaluation, and every outcome in order. Step through the full session timeline.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="5 3 19 12 5 21 5 3" />
      </svg>
    ),
  },
  {
    title: "Chain Verification",
    description:
      "One API call verifies the integrity of your entire audit chain. If a single record was altered or deleted, the chain breaks — and we tell you exactly where.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    ),
  },
  {
    title: "Anomaly Detection",
    description:
      "Automated detection of latency spikes, cost outliers, and deny clusters. Surface suspicious agent behavior before it becomes an incident.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
  },
  {
    title: "Forensic Export",
    description:
      "Export forensic reports as JSON with chain-of-custody certificates, or as CSV for spreadsheet analysis. Built for auditors, not just engineers.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </svg>
    ),
  },
  {
    title: "Shadow Agent Detection",
    description:
      "Automatically detect unregistered agents attempting to access your infrastructure. Surface rogue agents through denied request patterns.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    ),
  },
];

const pillars = [
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
    capability: "HMAC-verifiable audit logs, automated compliance assessments.",
  },
  {
    pillar: "Forensics",
    question: "What happened, provably?",
    capability: "Hash-chained logs, incident replay, export, chain verification.",
  },
];

const complianceMapping = [
  {
    framework: "EU AI Act",
    requirement: "Traceability & record-keeping (Art. 12)",
    forensicControl: "HMAC-chained audit trail with full request metadata, configurable retention, and evidence export.",
  },
  {
    framework: "SOC 2 Type II",
    requirement: "Tamper-evident audit logging",
    forensicControl: "Cryptographic hash chain where altering one record breaks the entire chain. Independently verifiable.",
  },
  {
    framework: "HIPAA",
    requirement: "Audit controls (164.312(b))",
    forensicControl: "Per-agent activity logging with attribution, chain-of-custody certificates for evidence export.",
  },
  {
    framework: "NIST AI RMF",
    requirement: "Agent observability & integrity",
    forensicControl: "Continuous monitoring, anomaly detection, forensic replay of agent decision sequences.",
  },
];

export default function Forensics() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">AI Forensics</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Reconstruct. Verify.{" "}
            <span className="text-[rgb(166,218,255)]">Prove It.</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            AI Forensics is the ability to reconstruct an agent&apos;s entire decision chain, prove it hasn&apos;t been altered, and export it as evidence for security, compliance, and legal teams.
          </p>
        </div>
      </section>

      {/* Monitoring vs Forensics */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">
            Monitoring tells you something broke.
          </h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Forensics tells you which agent did it, what it was trying to do, and whether the audit chain was tampered with.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-gray-500" />
                <h3 className="text-base font-semibold text-gray-400">Monitoring / Observability</h3>
              </div>
              <ul className="space-y-3 text-sm text-gray-500">
                <li className="flex items-start gap-2"><span className="shrink-0 mt-0.5">•</span>What&apos;s happening now?</li>
                <li className="flex items-start gap-2"><span className="shrink-0 mt-0.5">•</span>Metrics, traces, APM dashboards</li>
                <li className="flex items-start gap-2"><span className="shrink-0 mt-0.5">•</span>Application-level logs (mutable)</li>
                <li className="flex items-start gap-2"><span className="shrink-0 mt-0.5">•</span>Alert when something goes wrong</li>
              </ul>
            </div>
            <div className="bg-[rgb(166,218,255)]/[0.03] border border-[rgb(166,218,255)]/20 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-[rgb(166,218,255)]" />
                <h3 className="text-base font-semibold text-[rgb(166,218,255)]">AI Forensics</h3>
              </div>
              <ul className="space-y-3 text-sm text-gray-300">
                <li className="flex items-start gap-2"><span className="text-[rgb(166,218,255)] shrink-0 mt-0.5">✓</span>What exactly happened, provably?</li>
                <li className="flex items-start gap-2"><span className="text-[rgb(166,218,255)] shrink-0 mt-0.5">✓</span>Cryptographic chain of evidence</li>
                <li className="flex items-start gap-2"><span className="text-[rgb(166,218,255)] shrink-0 mt-0.5">✓</span>Tamper-evident, independently verifiable</li>
                <li className="flex items-start gap-2"><span className="text-[rgb(166,218,255)] shrink-0 mt-0.5">✓</span>Reconstruct and replay any incident</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Forensic Features Grid */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Forensic Capabilities</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Every capability is built into the platform — not bolted on after the fact.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {forensicFeatures.map((feature) => (
              <div key={feature.title} className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 hover:border-[rgb(166,218,255)]/30 hover:bg-[rgb(166,218,255)]/[0.03] transition-all group">
                <div className="w-10 h-10 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center text-[rgb(166,218,255)] mb-4 group-hover:bg-[rgb(166,218,255)]/20 transition-colors">
                  {feature.icon}
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Four Pillars */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">The Four Pillars of AI Agent Governance</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Most solutions cover one or two. AI Identity covers all four.
          </p>
          <div className="overflow-hidden rounded-xl border border-white/10">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-white/[0.05]">
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">Pillar</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">Core Question</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">AI Identity Capability</th>
                </tr>
              </thead>
              <tbody>
                {pillars.map((p, i) => (
                  <tr key={p.pillar} className={`${i % 2 === 0 ? "bg-white/[0.02]" : "bg-transparent"} ${p.pillar === "Forensics" ? "border-l-2 border-l-[rgb(166,218,255)]" : ""}`}>
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

      {/* Compliance Mapping */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Forensics Meets Compliance</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            AI Forensics isn&apos;t optional — it&apos;s what regulators are already requiring.
          </p>
          <div className="space-y-4">
            {complianceMapping.map((c) => (
              <div key={c.framework} className="bg-white/[0.03] border border-white/10 rounded-xl p-6 flex flex-col sm:flex-row sm:items-start gap-4">
                <div className="sm:w-40 flex-shrink-0">
                  <h3 className="text-base font-semibold text-white">{c.framework}</h3>
                  <span className="text-xs text-gray-500">{c.requirement}</span>
                </div>
                <p className="text-sm text-gray-400 leading-relaxed">{c.forensicControl}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">If it didn&apos;t go through AI Identity, you can&apos;t prove what your agent did.</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Start with the free tier — 5 agents, tamper-proof audit trails, and chain verification included.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link href="https://dashboard.ai-identity.co" className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
                Start Free
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </Link>
              <Link href="/security" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                View Security Architecture
              </Link>
              <Link href="/forensics-pipeline.html" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                Explore the Technical Architecture
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
