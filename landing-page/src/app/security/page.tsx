import type { Metadata } from "next";
import Link from "next/link";
import { generatePageMetadata } from "@/lib/metadata";

export const metadata: Metadata = generatePageMetadata({
  title: "Zero-Trust Security for AI Agents",
  description:
    "Enterprise-grade security for autonomous AI agents. Fail-closed enforcement, AES-256 encrypted credential vault, tamper-evident audit trails, and tenant isolation.",
  path: "/security",
});

const securityFeatures = [
  {
    title: "Zero-Trust Architecture",
    description:
      "Every request is authenticated and authorized before processing. No implicit trust, no shortcuts. The gateway validates agent identity, checks policy, and logs the result before any request reaches an LLM provider.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
  {
    title: "Fail-Closed by Default",
    description:
      "If something goes wrong during policy evaluation — timeout, error, ambiguity — the request is denied. Agents cannot bypass controls, even during partial outages. Security is the default, not the exception.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
  {
    title: "Encrypted Credential Vault",
    description:
      "LLM provider API keys are stored encrypted at rest (AES-256) and only decrypted in-memory at request time. Agents never see or handle raw provider credentials.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
      </svg>
    ),
  },
  {
    title: "Tamper-Evident Audit Trail",
    description:
      "Every audit record is cryptographically chained using HMAC-SHA256. Each entry includes the hash of the previous entry, creating an unbroken chain. Alter one record and the chain breaks — making tampering detectable and provable.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    title: "Tenant Isolation",
    description:
      "Row-level security at the database layer ensures complete data isolation between tenants. One customer's agents, policies, keys, and audit logs can never leak into another's — even in the event of an application-level vulnerability.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    title: "Key Separation",
    description:
      "Organization keys (for management) and agent keys (for LLM requests) are fully separated. Compromising an agent's runtime key does not grant access to management operations or other agents.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="12 2 2 7 12 12 22 7 12 2" />
        <polyline points="2 17 12 22 22 17" />
        <polyline points="2 12 12 17 22 12" />
      </svg>
    ),
  },
];

const compliance = [
  {
    framework: "SOC 2 Type II",
    status: "Architecture aligned",
    desc: "Logical access controls, tamper-evident audit trail, encryption, tenant isolation.",
  },
  {
    framework: "NIST AI RMF",
    status: "Framework supported",
    desc: "Agent observability, policy governance, cryptographic integrity, fail-closed design.",
  },
  {
    framework: "EU AI Act",
    status: "High-risk ready",
    desc: "Human oversight, traceability, transparent enforcement, audit log export.",
  },
];

export default function Security() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Security</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Enterprise-Grade <span className="text-[rgb(166,218,255)]">Security</span> for AI Agents
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            AI Identity is built with security as the foundation, not an afterthought. Zero-trust architecture, encrypted credential management, and tamper-evident audit trails — designed for regulated industries.
          </p>
        </div>
      </section>

      {/* Security Features Grid */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {securityFeatures.map((feature) => (
            <div key={feature.title} className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 hover:border-[rgb(166,218,255)]/30 hover:bg-[rgb(166,218,255)]/[0.03] transition-all group">
              <div className="w-10 h-10 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center text-[rgb(166,218,255)] mb-4 group-hover:bg-[rgb(166,218,255)]/20 transition-colors">
                {feature.icon}
              </div>
              <h3 className="text-base font-semibold text-white mb-2">{feature.title}</h3>
              <p className="text-sm text-gray-400 leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Compliance */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Compliance Alignment</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Built to satisfy the frameworks your security and compliance teams care about most.
          </p>
          <div className="space-y-4">
            {compliance.map((c) => (
              <div key={c.framework} className="bg-white/[0.03] border border-white/10 rounded-xl p-6 flex flex-col sm:flex-row sm:items-center gap-4">
                <div className="sm:w-48 flex-shrink-0">
                  <h3 className="text-base font-semibold text-white">{c.framework}</h3>
                  <span className="text-xs text-[rgb(166,218,255)] font-medium">{c.status}</span>
                </div>
                <p className="text-sm text-gray-400 leading-relaxed">{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">Want the full security deep-dive?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Read our architecture documentation or schedule a call with our team to discuss how AI Identity fits your security requirements.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link href="/architecture" className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
                View Architecture
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </Link>
              <Link href="/contact" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                Schedule a Call
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
