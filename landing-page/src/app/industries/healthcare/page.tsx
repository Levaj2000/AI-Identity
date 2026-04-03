import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import Link from "next/link";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Agent Governance for Healthcare",
  description: "Govern AI agents in healthcare with per-agent identity, HIPAA-ready audit trails, and human-in-the-loop gates. Pre-mapped to EU AI Act, HIPAA, HITECH, and FDA AI/ML requirements.",
  path: "/industries/healthcare",
});

const regulations = [
  { name: "EU AI Act", detail: "Healthcare diagnostics classified as high-risk AI. Requires risk management, human oversight, transparency, and conformity assessment for clinical AI systems." },
  { name: "HIPAA", detail: "The Privacy and Security Rules mandate strict access controls, audit trails, and minimum necessary access for any system handling Protected Health Information (PHI)." },
  { name: "HITECH Act", detail: "Strengthens HIPAA enforcement with breach notification requirements and increased penalties. Extends accountability to business associates handling PHI." },
  { name: "FDA AI/ML Guidance", detail: "Evolving framework for AI/ML-based Software as a Medical Device (SaMD). Requires predetermined change control plans and real-world performance monitoring." },
  { name: "GDPR", detail: "Article 22 and Article 9 impose heightened protections for automated processing of health data. Explicit consent and data protection impact assessments required." },
];

const challenges = [
  {
    title: "PHI Exposure Through Shared Credentials",
    description: "Multiple clinical AI agents share the same service account. A triage agent and a billing agent both access patient records with identical permissions — violating the HIPAA minimum necessary standard.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>,
  },
  {
    title: "No Audit Trail of AI-Assisted Diagnoses",
    description: "When a diagnostic AI agent contributes to a clinical decision, there&apos;s no tamper-proof record of what data it accessed, what model it used, or what reasoning it provided.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>,
  },
  {
    title: "No Proof of Human Oversight",
    description: "Regulators and patients need evidence that a qualified human reviewed AI-assisted clinical decisions. Without enforced approval gates, demonstrating oversight is impossible.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>,
  },
  {
    title: "Unscoped Patient Data Access",
    description: "AI agents access patient data without granular permissions. A scheduling agent can read diagnostic records, and a research agent can access identifiable patient information without consent.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
  },
];

const solutions = [
  {
    title: "Per-Agent Identity with PHI Scoping",
    description: "Every clinical, administrative, and research agent gets a unique cryptographic identity with permissions scoped to exactly the PHI it needs — enforcing HIPAA&apos;s minimum necessary standard.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
  },
  {
    title: "HIPAA-Ready Audit Trails",
    description: "HMAC-SHA256 chained logs capture every agent action with full provenance. Tamper-proof records satisfy HIPAA audit requirements and HITECH breach investigation needs.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>,
  },
  {
    title: "Human-in-the-Loop Gates",
    description: "Enforce mandatory human review for clinical decision agents. Configurable approval workflows ensure qualified oversight before AI-assisted diagnoses reach patients.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>,
  },
  {
    title: "Healthcare Compliance Assessments",
    description: "Automated compliance checks pre-mapped to HIPAA, HITECH, EU AI Act, and FDA AI/ML guidance. Generate audit-ready reports and identify gaps before regulators do.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>,
  },
];

const complianceMapping = [
  { framework: "EU AI Act (High-Risk)", requirement: "Risk management for clinical AI systems", capability: "Automated risk assessments with per-agent scoring and continuous monitoring" },
  { framework: "EU AI Act (High-Risk)", requirement: "Human oversight of diagnostic AI", capability: "Mandatory human-in-the-loop approval gates for clinical decision agents" },
  { framework: "HIPAA Privacy Rule", requirement: "Minimum necessary access to PHI", capability: "Per-agent credentials scoped to exactly the patient data each agent needs" },
  { framework: "HIPAA Security Rule", requirement: "Audit controls and activity logging", capability: "HMAC-chained tamper-proof audit trail of every PHI access event" },
  { framework: "HIPAA Security Rule", requirement: "Access controls and authentication", capability: "Unique cryptographic identity per agent with role-based permissions" },
  { framework: "HITECH Act", requirement: "Breach notification and investigation", capability: "Forensic replay and evidence export for breach investigation and reporting" },
  { framework: "FDA AI/ML Guidance", requirement: "Real-world performance monitoring", capability: "Continuous agent monitoring with anomaly detection and policy enforcement" },
  { framework: "FDA AI/ML Guidance", requirement: "Predetermined change control plan", capability: "Policy-as-code enforcement with versioned agent configurations" },
  { framework: "GDPR Article 9", requirement: "Special category data protections", capability: "Granular access controls and consent-based data scoping for health data" },
];

export default function IndustryHealthcare() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Healthcare</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            AI Agent Governance for{" "}
            <span className="text-[rgb(166,218,255)]">Healthcare</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            Healthcare AI agents handle the most sensitive data in existence.
            AI Identity delivers per-agent identity, HIPAA-ready audit trails, and
            human-in-the-loop enforcement for clinical AI systems.
          </p>
        </div>
      </section>

      {/* Regulatory Landscape */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Regulatory Landscape</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Healthcare AI agents face the strictest regulatory requirements of any industry. Violations carry criminal penalties, not just fines.
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
            Healthcare organizations deploying AI agents face unique governance challenges where failures put patient safety at risk.
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
            Purpose-built agent governance that maps directly to healthcare regulatory requirements.
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
            See exactly how AI Identity capabilities map to healthcare regulatory requirements.
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
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">Ready to govern your healthcare AI agents?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Start with AI Identity for free. Per-agent identity, HIPAA-ready audit trails, and human-in-the-loop gates for clinical AI systems.
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
