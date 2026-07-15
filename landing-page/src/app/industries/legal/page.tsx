import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import Link from "next/link";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Forensics for Legal",
  description: "Forensic-grade audit trails for legal AI agents. HMAC-chained logs + DSSE-signed attestations protect privilege and support e-discovery workflows — tamper-evident, verifiable offline.",
  path: "/industries/legal",
});

const regulations = [
  { name: "ABA Model Rule 1.6", detail: "The duty of confidentiality covers every system that touches client information. Firms must make reasonable efforts to prevent unauthorized access to client data — including access by AI tools." },
  { name: "ABA Model Rules 1.1 & 5.3", detail: "The duty of competence extends to technology, and lawyers must supervise nonlawyer assistance — which bar guidance increasingly reads to include AI tools working on client matters." },
  { name: "FRCP 26 & 34", detail: "E-discovery rules govern the preservation and production of electronically stored information. Producing parties must be able to explain how ESI was collected, processed, and kept intact." },
  { name: "FRCP 37(e)", detail: "Sanctions for failure to preserve ESI. When AI agents touch documents under a litigation hold, you need to show the records weren't altered or lost." },
  { name: "Court AI Standing Orders", detail: "A growing number of courts require parties to disclose or certify generative AI use in filings. Firms need a reliable record of where AI contributed and who reviewed it." },
  { name: "EU AI Act", detail: "AI systems used in the administration of justice are classified as high-risk under Annex III. Requires risk management, human oversight, transparency, and record-keeping." },
];

const challenges = [
  {
    title: "Privileged Data Access Through Shared Credentials",
    description: "Research, drafting, and intake agents share the same service account. There's no way to show which agent touched privileged material — and no way to enforce ethical walls between matters.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>,
  },
  {
    title: "No Defensible Audit Trail for AI-Assisted Work",
    description: "When an AI agent contributes to a brief, a contract review, or a due-diligence memo, there's no tamper-evident record of what it accessed, which model produced the output, or who reviewed it.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>,
  },
  {
    title: "Chain of Custody for AI-Touched Evidence",
    description: "AI agents collect, process, and summarize documents in discovery. When opposing counsel challenges the integrity of that evidence, fragmented application logs can't reconstruct what happened to it.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
  },
  {
    title: "No Proof of Attorney Oversight",
    description: "Courts and bar regulators expect a qualified attorney to review AI-assisted work before it goes out the door. Without enforced review gates, demonstrating that supervision is guesswork.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>,
  },
];

const solutions = [
  {
    title: "Per-Agent Identity with Matter-Level Scoping",
    description: "Every research, drafting, and discovery agent gets a unique cryptographic identity with permissions scoped to the matters and clients it's authorized for — enforcing ethical walls in code, not policy memos.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
  },
  {
    title: "Tamper-Evident Chained Audit Logs",
    description: "HMAC-SHA256 chained logs capture every agent action with full provenance — what was accessed, which model ran, what it produced. Any alteration breaks the chain and is immediately detectable.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>,
  },
  {
    title: "Case File Export with Offline Verification",
    description: "One-click export of a signed evidence bundle — designed for e-discovery workflows. Anyone can verify its integrity with an open-source CLI, offline, without trusting us or touching our servers.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>,
  },
  {
    title: "Attorney-in-the-Loop Gates",
    description: "Enforce mandatory attorney review before AI-assisted work product is filed or sent. Each approval is recorded in the audit chain — so supervision is provable, not just asserted.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>,
  },
];

const complianceMapping = [
  { framework: "ABA Model Rule 1.6", requirement: "Reasonable efforts to protect client confidences", capability: "Per-agent credentials scoped to exactly the matters each agent is authorized for" },
  { framework: "ABA Model Rule 5.3", requirement: "Supervision of nonlawyer (and AI) assistance", capability: "Attorney-in-the-loop approval gates recorded in the audit chain" },
  { framework: "ABA Model Rule 1.1", requirement: "Technological competence with AI tools", capability: "Model and version provenance captured in every audit record" },
  { framework: "FRCP 26 & 34", requirement: "Defensible collection and production of ESI", capability: "Case File export with cryptographic integrity proofs and offline verification" },
  { framework: "FRCP 37(e)", requirement: "Preservation of ESI under litigation hold", capability: "HMAC-chained logs make any alteration or deletion immediately detectable" },
  { framework: "Court AI Standing Orders", requirement: "Disclosure and certification of AI use", capability: "Verifiable record of where AI contributed and which attorney reviewed it" },
  { framework: "EU AI Act (Annex III)", requirement: "Human oversight and record-keeping for high-risk AI", capability: "Enforced review gates plus tamper-evident logging of every agent action" },
  { framework: "GDPR Article 22", requirement: "Right to contest automated decisions", capability: "Forensic replay of any agent decision chain with full provenance" },
];

export default function IndustryLegal() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Legal</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Forensic Evidence for{" "}
            <span className="text-[rgb(166,218,255)]">Legal AI</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            Legal AI agents touch privileged documents, discovery material, and client confidences. When their work is challenged — by opposing counsel, a court, or a bar regulator — you need a tamper-evident, cryptographically-signed record of exactly what happened. AI Identity gives every agent action a forensic audit trail that verifies offline.
          </p>
        </div>
      </section>

      {/* Regulatory Landscape */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Regulatory Landscape</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Legal AI operates under professional-responsibility rules, procedural rules, and AI regulation at once. Failures risk privilege, sanctions, and bar discipline.
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
            Law firms and legal departments deploying AI agents face governance gaps where a single failure can compromise privilege or an entire matter.
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
            Purpose-built agent governance that maps directly to the rules legal work is judged by.
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
            See exactly how AI Identity capabilities map to the rules that govern legal AI.
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
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">Ready for defensible legal AI?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              We&apos;re onboarding design partners in legal. Get hands-on access to the forensic audit chain, shape the v1.0 spec, lock in preferred pricing.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link
                href="/contact?intent=design-partner"
                className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
              >
                Request Design Partner Access
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </Link>
              <Link href="/#replay-demo" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3" /></svg>
                View Incident Replay Demo
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
