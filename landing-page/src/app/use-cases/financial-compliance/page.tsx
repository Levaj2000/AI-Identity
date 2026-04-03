import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import Link from "next/link";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Agent Identity for Financial Compliance",
  description: "Govern AI agents in financial services. SOC 2 and EU AI Act compliant audit trails, per-agent credentials, and policy enforcement for regulated environments.",
  path: "/use-cases/financial-compliance",
});

const challenges = [
  {
    title: "Regulatory Mandates",
    description: "SEC, FINRA, MiFID II, and the EU AI Act require documented oversight of automated decision-making. Manual processes can&apos;t keep up.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>,
  },
  {
    title: "Tamper Risk",
    description: "Standard logging can be modified after the fact. Regulators need proof that records haven&apos;t been altered &mdash; not just a promise.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
  },
  {
    title: "Compliance Gaps",
    description: "Your AI agents make thousands of decisions daily. You need to prove each one followed policy &mdash; retroactively, on demand, under audit.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>,
  },
];

const solutions = [
  {
    title: "HMAC-Chained Audit Logs",
    description: "Every agent action is cryptographically chained. Any tampering breaks the chain and is immediately detectable &mdash; provable in court.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>,
  },
  {
    title: "Automated Compliance Assessments",
    description: "Run your agent fleet against NIST AI RMF, SOC 2, EU AI Act, and ISO 42001 frameworks. Get a score and remediation steps.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>,
  },
  {
    title: "Forensic Export",
    description: "One-click evidence packages for regulators. Timeline reconstruction, policy verification, and integrity proofs &mdash; audit-ready.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>,
  },
  {
    title: "Real-Time Monitoring",
    description: "Flag policy violations as they happen, not weeks later during an audit. Fail-closed enforcement means violations are blocked, not just logged.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>,
  },
];

const codeExample = `from ai_identity import AIIdentityClient

async with AIIdentityClient(api_key="aid_sk_...") as client:
    # Verify the audit chain hasn't been tampered with
    verification = await client.audit.verify_chain(
        agent_id="agent_8f3a..."
    )
    print(f"Chain valid: {verification.valid}")
    print(f"Records checked: {verification.entries_verified}")

    # Pull audit stats for compliance reporting
    stats = await client.audit.stats(agent_id="agent_8f3a...")
    print(f"Total events: {stats.total_events}")
    print(f"Denied requests: {stats.denied_count}")

    # Pull full audit logs for regulatory export
    logs = await client.audit.list(
        agent_id="agent_8f3a...",
        limit=1000,
    )
    print(f"Total auditable actions: {logs.total}")`;

export default function UseCaseFinancialAgent() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Use Case</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Meet Regulatory Requirements for{" "}
            <span className="text-[rgb(166,218,255)]">Financial</span>{" "}
            AI Agents
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            Financial regulators demand auditability. AI Identity delivers
            tamper-proof evidence for every agent decision &mdash; HMAC-chained logs,
            automated compliance checks, and one-click forensic exports.
          </p>
        </div>
      </section>

      {/* The Challenge */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">The Challenge</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            In finance, what you can&apos;t prove didn&apos;t happen. Regulators demand receipts.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {challenges.map((c) => (
              <div key={c.title} className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
                <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center text-red-400 mb-4">
                  {c.icon}
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{c.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{c.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How AI Identity Solves This */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">How AI Identity Solves This</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Cryptographic proof of every agent action, built for regulated industries.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {solutions.map((s) => (
              <div key={s.title} className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 hover:border-[rgb(166,218,255)]/30 hover:bg-[rgb(166,218,255)]/[0.03] transition-all group">
                <div className="w-10 h-10 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center text-[rgb(166,218,255)] mb-4 group-hover:bg-[rgb(166,218,255)]/20 transition-colors">
                  {s.icon}
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{s.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{s.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Code Example */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">See It in Action</h2>
          <p className="text-sm text-gray-400 text-center mb-8 max-w-[560px] mx-auto">
            Verify audit integrity and pull compliance data in a few lines.
          </p>
          <div className="bg-[rgb(16,19,28)] border border-white/10 rounded-2xl overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5">
              <span className="text-xs text-[rgb(166,218,255)] font-medium">Python</span>
            </div>
            <pre className="p-5 overflow-x-auto text-sm text-gray-300 leading-relaxed">
              <code>{codeExample}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">Ready for audit-proof AI agents?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Start with AI Identity for free &mdash; tamper-proof audit logs and compliance assessments from day one.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link href="/pricing" className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
                Get Started Free
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </Link>
              <Link href="/docs" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                Read the Docs
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
