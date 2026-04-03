import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import Link from "next/link";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Agent Governance for Financial Services",
  description: "Govern AI agents in financial services with per-agent identity, tamper-proof audit trails, and policy enforcement. Pre-mapped to EU AI Act, SOC 2, PCI-DSS, NYDFS, and SEC requirements.",
  path: "/industries/finance",
});

const regulations = [
  { name: "EU AI Act", detail: "Credit scoring classified as high-risk under Annex III. Requires human oversight, transparency, and risk management for AI systems making creditworthiness assessments." },
  { name: "SOC 2 Type II", detail: "Continuous monitoring of controls over security, availability, and confidentiality. Auditors need evidence that agent access is scoped and logged." },
  { name: "PCI-DSS", detail: "Strict requirements for any system touching cardholder data. Agents processing payments need isolated credentials and audit trails." },
  { name: "NYDFS Cybersecurity Regulation", detail: "23 NYCRR 500 mandates access controls, audit trails, and risk assessments for all information systems — including autonomous AI agents." },
  { name: "SEC AI Guidance", detail: "Evolving requirements for AI-driven advisory and trading systems. Firms must demonstrate oversight and explainability for automated decisions." },
  { name: "GDPR", detail: "Article 22 governs automated decision-making. Individuals have the right to contest decisions made without meaningful human involvement." },
];

const challenges = [
  {
    title: "Shared API Keys Across Trading Agents",
    description: "Multiple trading agents share a single LLM API key. When one agent makes an unauthorized trade, there&apos;s no way to attribute the action or revoke access without breaking all agents.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>,
  },
  {
    title: "No Audit Trail for Automated Decisions",
    description: "AI agents execute thousands of trades and credit decisions daily. When regulators ask for evidence of oversight, your team scrambles to reconstruct what happened from fragmented logs.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>,
  },
  {
    title: "Credit Scoring Without Per-Agent Identity",
    description: "Credit scoring agents operate under generic service accounts. There&apos;s no way to verify which model version made a specific credit decision or enforce different policies per use case.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>,
  },
  {
    title: "Liability for Unauthorized Transactions",
    description: "When an AI agent executes an unauthorized transaction, who&apos;s responsible? Without per-agent identity and policy enforcement, liability is ambiguous and exposure is unlimited.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
  },
];

const solutions = [
  {
    title: "Per-Agent Credentials",
    description: "Every trading, lending, and compliance agent gets a unique cryptographic identity with scoped API keys. Revoke one agent without disrupting your fleet.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
  },
  {
    title: "Tamper-Proof Audit Trails",
    description: "HMAC-SHA256 chained logs for every agent action. Any modification breaks the chain and is immediately detectable — satisfying financial regulators&apos; evidence requirements.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>,
  },
  {
    title: "Policy Enforcement",
    description: "Set budget caps, model access controls, and time-of-day restrictions per agent. A trading agent can&apos;t exceed its risk limit, and a compliance agent can&apos;t access trading models.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>,
  },
  {
    title: "Financial Compliance Dashboards",
    description: "Pre-mapped compliance assessments for SOC 2, EU AI Act, PCI-DSS, and NYDFS. Run automated checks and generate audit-ready reports in one click.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>,
  },
];

const complianceMapping = [
  { framework: "EU AI Act (Annex III)", requirement: "Risk management system for high-risk AI", capability: "Automated risk assessments with per-agent scoring and policy enforcement" },
  { framework: "EU AI Act (Annex III)", requirement: "Human oversight of credit scoring AI", capability: "Human-in-the-loop approval gates for credit decisions above threshold" },
  { framework: "SOC 2 Type II", requirement: "Logical access controls and monitoring", capability: "Per-agent credentials with scoped permissions and real-time monitoring" },
  { framework: "SOC 2 Type II", requirement: "Audit logging and change detection", capability: "HMAC-chained tamper-proof audit trail with integrity verification" },
  { framework: "PCI-DSS", requirement: "Unique ID for each person with computer access", capability: "Unique cryptographic identity per agent with individual API keys" },
  { framework: "PCI-DSS", requirement: "Track and monitor all access to cardholder data", capability: "Complete audit trail of every agent request touching payment data" },
  { framework: "NYDFS 23 NYCRR 500", requirement: "Access privileges and audit trail", capability: "Least-privilege agent permissions with immutable activity logs" },
  { framework: "SEC AI Guidance", requirement: "Oversight of AI-driven advisory decisions", capability: "Policy-as-code enforcement with automated compliance checks" },
  { framework: "GDPR Article 22", requirement: "Right to contest automated decisions", capability: "Forensic replay of any agent decision chain with full provenance" },
];

export default function IndustryFinance() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Financial Services</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            AI Agent Governance for{" "}
            <span className="text-[rgb(166,218,255)]">Financial Services</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            Financial regulators demand proof of oversight for every AI-driven decision.
            AI Identity delivers per-agent identity, tamper-proof audit trails, and
            policy enforcement built for the most regulated industry on earth.
          </p>
        </div>
      </section>

      {/* Regulatory Landscape */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Regulatory Landscape</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Financial services AI agents operate under overlapping regulatory frameworks. Non-compliance means fines, enforcement actions, and reputational damage.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {regulations.map((r) => (
              <div key={r.name} className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
                <h3 className="text-base font-semibold text-[rgb(166,218,255)] mb-2">{r.name}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{r.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Industry Challenges */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Industry Challenges</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Financial institutions deploying AI agents face governance gaps that create regulatory and operational risk.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
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
            Purpose-built agent governance that maps directly to financial regulatory requirements.
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

      {/* Compliance Mapping Table */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Compliance Mapping</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            See exactly how AI Identity capabilities map to financial regulatory requirements.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left text-sm font-semibold text-[rgb(166,218,255)] py-3 px-4">Framework</th>
                  <th className="text-left text-sm font-semibold text-[rgb(166,218,255)] py-3 px-4">Requirement</th>
                  <th className="text-left text-sm font-semibold text-[rgb(166,218,255)] py-3 px-4">AI Identity Capability</th>
                </tr>
              </thead>
              <tbody>
                {complianceMapping.map((row, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                    <td className="text-sm text-gray-300 py-3 px-4 font-medium">{row.framework}</td>
                    <td className="text-sm text-gray-400 py-3 px-4">{row.requirement}</td>
                    <td className="text-sm text-gray-400 py-3 px-4">{row.capability}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">Ready to govern your financial AI agents?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Start with AI Identity for free. Per-agent credentials, tamper-proof audit trails, and compliance dashboards pre-mapped to financial frameworks.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <a
                href="https://dashboard.ai-identity.co"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
              >
                Get Started Free
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </a>
              <Link href="/contact" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                Talk to Sales
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
