import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import Link from "next/link";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Identity vs Valence Security — AI Agent Governance Comparison",
  description:
    "Compare AI Identity and Valence Security for AI agent governance. See why teams choose AI Identity's fail-closed enforcement and forensic audit trails over Valence's posture management approach.",
  path: "/vs/valence",
});

const features = [
  { feature: "Cryptographic Per-Agent Identity (aid_sk_ keys)", aiIdentity: true, competitor: false },
  { feature: "Fail-Closed Enforcement Gateway", aiIdentity: true, competitor: false },
  { feature: "HMAC-SHA256 Tamper-Proof Audit Trails", aiIdentity: true, competitor: false },
  { feature: "Decision-Level Forensic Replay", aiIdentity: true, competitor: false },
  { feature: "Granular Spending Limits Per Agent", aiIdentity: true, competitor: false },
  { feature: "Shadow AI / Agent Discovery", aiIdentity: false, competitor: true },
  { feature: "SaaS Security Posture Management (SSPM)", aiIdentity: false, competitor: true },
  { feature: "Identity Threat Detection (ITDR)", aiIdentity: false, competitor: true },
  { feature: "One-Click SaaS Remediation", aiIdentity: false, competitor: true },
  { feature: "Framework Integration (LangChain, CrewAI)", aiIdentity: true, competitor: false },
  { feature: "15-Minute Integration (One URL Change)", aiIdentity: true, competitor: false },
  { feature: "Cross-Framework Agent Governance", aiIdentity: true, competitor: false },
];

const shortcomings = [
  {
    title: "Posture Management, Not Enforcement",
    description:
      "Valence discovers agent permissions and flags risks. But it cannot intercept and block an agent action in real time. AI Identity's gateway evaluates policy before every request proceeds — if an agent is not authorized, the request is denied before it executes.",
  },
  {
    title: "No Cryptographic Identity or Forensics",
    description:
      "Valence operates on configuration data and permission snapshots. It does not cryptographically bind identity to agent sessions or produce hash-chained audit trails. The audit record is monitoring-based, not forensic-grade.",
  },
  {
    title: "SaaS-Scoped Architecture",
    description:
      "Valence is built for agents living inside SaaS ecosystems — it discovers agents connected to SaaS tools. It does not natively govern agents built on LangChain, CrewAI, or other agentic frameworks that operate outside SaaS boundaries.",
  },
  {
    title: "Human-Triggered Remediation",
    description:
      "Valence's one-click remediation requires a security team member to be watching the dashboard and clicking the button. This is not autonomous enforcement — it is human-gated response to discovered risks.",
  },
];

const differentiators = [
  {
    title: "Real-Time Enforcement",
    description:
      "Every agent request is evaluated against policy before execution. Deny-by-default. No gap between detection and enforcement.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
      </svg>
    ),
  },
  {
    title: "Tamper-Evident Forensics",
    description:
      "HMAC-SHA256 hash-chained audit trails that cannot be altered without detection. Exportable evidence with chain-of-custody verification for regulators.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    title: "Framework-Native Integration",
    description:
      "Built for LangChain, CrewAI, and custom agent frameworks. One URL change to integrate, not a platform onboarding process.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="9 11 12 14 22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
  },
  {
    title: "Agent Spending Controls",
    description:
      "Set per-agent, per-tool spending limits. Prevent runaway API costs from autonomous agents before they happen — a risk surface Valence does not address.",
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

export default function CompareValence() {
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
            <span className="text-[rgb(166,218,255)]">Valence Security</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            Valence Security discovers and assesses SaaS and AI agent risk through
            posture management. AI Identity enforces policy at runtime and produces
            tamper-evident forensic evidence of every agent action.
          </p>
        </div>
      </section>

      {/* Feature Comparison Table */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Feature Comparison</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Side-by-side breakdown of capabilities that matter for production AI agent deployments.
          </p>
          <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
            <div className="grid grid-cols-[1fr_100px_100px] md:grid-cols-[1fr_140px_140px] text-sm">
              {/* Header */}
              <div className="px-5 py-4 border-b border-white/10 font-semibold text-gray-400">Feature</div>
              <div className="px-3 py-4 border-b border-white/10 font-semibold text-[rgb(166,218,255)] text-center">AI Identity</div>
              <div className="px-3 py-4 border-b border-white/10 font-semibold text-gray-400 text-center">Valence</div>
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

      {/* Where Valence Falls Short */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">
            Where Valence Falls Short for AI Agents
          </h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Valence tells you there is a problem. It does not stop the agent from doing the wrong thing.
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
            Runtime enforcement and forensic evidence, not just posture visibility.
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
              Ready to govern your AI agents?
            </h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Add identity, audit trails, and compliance to your agent fleet in 15 minutes. No SDK changes required.
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
