import { Link } from "react-router";
import SEO from "../components/SEO";

const features = [
  { feature: "Per-Agent Identity (aid_sk_ keys)", aiIdentity: true, competitor: false },
  { feature: "Human User Authentication (SSO, MFA)", aiIdentity: false, competitor: true },
  { feature: "Agent Lifecycle Management", aiIdentity: true, competitor: false },
  { feature: "LLM-Specific Policy Enforcement", aiIdentity: true, competitor: false },
  { feature: "HMAC-SHA256 Tamper-Proof Audit Trails", aiIdentity: true, competitor: false },
  { feature: "Chain-of-Thought Forensic Replay", aiIdentity: true, competitor: false },
  { feature: "Token Budget & Rate Limiting per Agent", aiIdentity: true, competitor: false },
  { feature: "EU AI Act Compliance Dashboard", aiIdentity: true, competitor: false },
  { feature: "SOC 2 / NIST AI RMF Reports", aiIdentity: true, competitor: false },
  { feature: "Sub-50ms Gateway Overhead", aiIdentity: true, competitor: true },
  { feature: "RBAC for Human Users", aiIdentity: true, competitor: true },
  { feature: "15-Minute Integration (One URL Change)", aiIdentity: true, competitor: false },
];

const shortcomings = [
  {
    title: "Built for Humans, Not Agents",
    description:
      "Okta and Auth0 authenticate human users with passwords, SSO, and MFA. Autonomous AI agents do not have passwords, do not click through login flows, and do not respond to push notifications.",
  },
  {
    title: "No Agent Lifecycle Management",
    description:
      "Traditional IAM has no concept of registering, versioning, suspending, or retiring an AI agent. Agents are not employees — they need a purpose-built identity layer.",
  },
  {
    title: "No LLM-Specific Policies",
    description:
      "Okta and Auth0 cannot enforce token budgets, restrict model access, block specific endpoints, or set time-of-day usage policies. They control who logs in, not what an agent does.",
  },
  {
    title: "No Chain-of-Thought Forensics",
    description:
      "Traditional IAM logs authentication events (login, logout, token refresh). It cannot capture or replay the reasoning steps an AI agent takes between receiving a prompt and producing a response.",
  },
];

const differentiators = [
  {
    title: "Purpose-Built for AI Agents",
    description:
      "AI Identity was designed from day one for autonomous agents. Per-agent aid_sk_ keys, scoped permissions, automated key rotation, and agent versioning are native primitives.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  {
    title: "Runtime Policy Enforcement",
    description:
      "Define which models an agent can call, set token budgets, enforce rate limits, and block restricted endpoints. Policies are enforced at the gateway in real time, not after the fact.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
  {
    title: "Tamper-Proof Forensics",
    description:
      "HMAC-SHA256 hash-chained audit trails capture every agent action with cryptographic integrity. Replay chain-of-thought reasoning for any incident investigation.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    title: "AI-Native Compliance",
    description:
      "Built-in dashboards for EU AI Act, SOC 2 Type II, and NIST AI RMF. Traditional IAM compliance covers human access controls, not autonomous agent behavior.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="9 11 12 14 22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
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

export default function CompareGenericIAM() {
  return (
    <>
      <SEO
        title="AI Identity vs Okta & Auth0 — Why Traditional IAM Fails for AI Agents"
        description="Compare AI Identity with traditional IAM solutions like Okta and Auth0. Learn why human-centric identity systems cannot govern autonomous AI agents and what to use instead."
        path="/vs/traditional-iam"
      />

      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Comparison</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            AI Identity vs{" "}
            <span className="text-[rgb(166,218,255)]">Traditional IAM</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            Okta and Auth0 secure human users. AI agents are not human.
            They need purpose-built identity infrastructure with LLM-aware policies,
            agent lifecycle management, and tamper-proof forensics.
          </p>
        </div>
      </section>

      {/* Feature Comparison Table */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Feature Comparison</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Traditional IAM solves a different problem. Here is where the gap shows up.
          </p>
          <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
            <div className="grid grid-cols-[1fr_100px_100px] md:grid-cols-[1fr_140px_140px] text-sm">
              {/* Header */}
              <div className="px-5 py-4 border-b border-white/10 font-semibold text-gray-400">Feature</div>
              <div className="px-3 py-4 border-b border-white/10 font-semibold text-[rgb(166,218,255)] text-center">AI Identity</div>
              <div className="px-3 py-4 border-b border-white/10 font-semibold text-gray-400 text-center">Okta / Auth0</div>
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

      {/* Where Traditional IAM Falls Short */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">
            Where Traditional IAM Falls Short for AI Agents
          </h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Human identity infrastructure was never designed for autonomous software agents.
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
            The identity layer your AI agents actually need.
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
              Your agents deserve their own identity layer
            </h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Stop shoehorning AI agents into human IAM. Get purpose-built agent identity, governance, and compliance in 15 minutes.
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
                to="/how-it-works"
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
