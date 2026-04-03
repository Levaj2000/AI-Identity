import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import Link from "next/link";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Identity vs Credo AI — AI Governance & Agent Identity Comparison",
  description:
    "Compare AI Identity and Credo AI for AI governance. See why teams choose AI Identity for runtime enforcement, per-agent identity, and accessible pricing over Credo AI's enterprise-only platform.",
  path: "/vs/credo-ai",
});

const features = [
  { feature: "Per-Agent Identity (aid_sk_ keys)", aiIdentity: true, competitor: false },
  { feature: "Runtime LLM Gateway", aiIdentity: true, competitor: false },
  { feature: "AI Governance & Risk Assessment", aiIdentity: true, competitor: true },
  { feature: "Policy-as-Code Enforcement", aiIdentity: true, competitor: true },
  { feature: "HMAC-SHA256 Tamper-Proof Audit Trails", aiIdentity: true, competitor: false },
  { feature: "Chain-of-Thought Forensic Replay", aiIdentity: true, competitor: false },
  { feature: "EU AI Act Compliance Dashboard", aiIdentity: true, competitor: true },
  { feature: "SOC 2 / NIST AI RMF Reports", aiIdentity: true, competitor: true },
  { feature: "Sub-50ms Gateway Overhead", aiIdentity: true, competitor: false },
  { feature: "15-Minute Integration (One URL Change)", aiIdentity: true, competitor: false },
  { feature: "Agent Lifecycle Management", aiIdentity: true, competitor: false },
  { feature: "Starts at $79/mo", aiIdentity: true, competitor: false },
];

const shortcomings = [
  {
    title: "No Runtime Gateway",
    description:
      "Credo AI governs AI models at the policy layer but cannot intercept or enforce rules at request time. Violations are detected after the fact, not blocked in real time.",
  },
  {
    title: "No Per-Agent Credentials",
    description:
      "Credo AI treats AI systems as monolithic units. It has no concept of individual agent identity, scoped API keys, or per-agent credential rotation.",
  },
  {
    title: "No Drop-In Integration",
    description:
      "Credo AI requires deep platform integration, custom connectors, and weeks of professional services to deploy. AI Identity takes 15 minutes with a single URL change.",
  },
  {
    title: "Enterprise-Only Pricing",
    description:
      "Credo AI targets enterprises with contracts typically starting above $100K/year. Startups and mid-market teams are priced out of production-grade AI governance.",
  },
];

const differentiators = [
  {
    title: "Runtime Enforcement, Not Just Policy",
    description:
      "AI Identity enforces policies at the gateway level in real time. Every request is authenticated, authorized, and logged before it reaches the LLM provider.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
  {
    title: "Cryptographic Agent Identity",
    description:
      "Every agent gets a unique aid_sk_ key with scoped permissions. Revoke, rotate, or audit any single agent without touching the rest of your fleet.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
      </svg>
    ),
  },
  {
    title: "Deploy in 15 Minutes",
    description:
      "Point your agents at the AI Identity gateway instead of calling LLM providers directly. One URL change, no SDK, no professional services engagement.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
  },
  {
    title: "Accessible Pricing",
    description:
      "AI Identity Pro starts at $79/mo for up to 50 agents. Get enterprise-grade governance without the enterprise price tag or multi-month procurement cycle.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="1" x2="12" y2="23" />
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
  },
];

function CheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgb(34,197,94)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgb(239,68,68)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

export default function CompareCredoAI() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Comparison</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            AI Identity vs{" "}
            <span className="text-[rgb(166,218,255)]">Credo AI</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            Credo AI is a recognized leader in enterprise AI governance.
            AI Identity delivers runtime enforcement, per-agent identity,
            and compliance dashboards at a fraction of the cost and deployment time.
          </p>
        </div>
      </section>

      {/* Feature Comparison Table */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Feature Comparison</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Governance is only half the story. See how runtime enforcement changes the equation.
          </p>
          <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
            <div className="grid grid-cols-[1fr_100px_100px] md:grid-cols-[1fr_140px_140px] text-sm">
              {/* Header */}
              <div className="px-5 py-4 border-b border-white/10 font-semibold text-gray-400">Feature</div>
              <div className="px-3 py-4 border-b border-white/10 font-semibold text-[rgb(166,218,255)] text-center">AI Identity</div>
              <div className="px-3 py-4 border-b border-white/10 font-semibold text-gray-400 text-center">Credo AI</div>
              {/* Rows */}
              {features.map((row, i) => (
                <>
                  <div key={`f-${i}`} className={`px-5 py-3.5 text-gray-300 ${i < features.length - 1 ? "border-b border-white/5" : ""}`}>
                    {row.feature}
                  </div>
                  <div key={`a-${i}`} className={`px-3 py-3.5 flex justify-center ${i < features.length - 1 ? "border-b border-white/5" : ""}`}>
                    {row.aiIdentity ? <CheckIcon /> : <XIcon />}
                  </div>
                  <div key={`c-${i}`} className={`px-3 py-3.5 flex justify-center ${i < features.length - 1 ? "border-b border-white/5" : ""}`}>
                    {row.competitor ? <CheckIcon /> : <XIcon />}
                  </div>
                </>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Where Credo AI Falls Short */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">
            Where Credo AI Falls Short for AI Agents
          </h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Credo AI governs models. AI Identity governs the agents that use them.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {shortcomings.map((item) => (
              <div key={item.title} className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
                <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center text-red-400 mb-4">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="15" y1="9" x2="9" y2="15" />
                    <line x1="9" y1="9" x2="15" y2="15" />
                  </svg>
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Teams Choose AI Identity */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">
            Why Teams Choose AI Identity
          </h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Runtime identity and governance that deploys in minutes, not months.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {differentiators.map((d) => (
              <div
                key={d.title}
                className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 hover:border-[rgb(166,218,255)]/30 hover:bg-[rgb(166,218,255)]/[0.03] transition-all group"
              >
                <div className="w-10 h-10 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center text-[rgb(166,218,255)] mb-4 group-hover:bg-[rgb(166,218,255)]/20 transition-colors">
                  {d.icon}
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{d.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{d.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">
              Enterprise governance without the enterprise price tag
            </h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Get started with AI Identity for free. Deploy in 15 minutes with a single URL change — no professional services required.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <a
                href="https://dashboard.ai-identity.co"
                className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
              >
                Start Free Trial
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </a>
              <Link
                href="/how-it-works"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
              >
                See How It Works
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
