import { Link } from "react-router";
import SEO, { makeHowToSchema } from "../components/SEO";

const steps = [
  {
    number: "01",
    title: "Register Your Agents",
    description: "Give each AI agent a unique, cryptographic identity. Every agent gets a verifiable fingerprint that follows it across every request — no more shared API keys.",
    details: ["Unique agent ID with metadata", "Scoped API keys per agent", "Automated key rotation and lifecycle management"],
  },
  {
    number: "02",
    title: "Define Policies",
    description: "Set fine-grained access controls per agent. Control which models an agent can call, enforce rate limits, set token budgets, and define time-of-day restrictions.",
    details: ["Policy-as-code enforcement", "Model-level access control", "Rate limiting and budget caps"],
  },
  {
    number: "03",
    title: "Route Through the Gateway",
    description: "Point your agents at the AI Identity gateway instead of calling LLM providers directly. One line of code. The gateway handles authentication, policy enforcement, and logging transparently.",
    details: ["Drop-in replacement — change one URL", "Works with OpenAI, Anthropic, Gemini, and more", "Sub-50ms overhead per request"],
  },
  {
    number: "04",
    title: "Monitor and Audit",
    description: "Every request is logged with a tamper-proof, HMAC-SHA256 hash-chained audit trail. View real-time dashboards, run compliance assessments, and export forensic evidence on demand.",
    details: ["Real-time agent activity dashboard", "Tamper-evident audit trail", "One-click compliance reports (EU AI Act, SOC 2, NIST)"],
  },
];

export default function HowItWorks() {
  return (
    <>
      <SEO
        title="How AI Agent Authentication Works"
        description="See how AI Identity registers agents, enforces policies, and captures audit logs — in 3 steps and under 15 minutes. One-line integration."
        path="/how-it-works"
        jsonLd={makeHowToSchema()}
      />
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">How It Works</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            From Integration to{" "}
            <span className="text-[rgb(166,218,255)]">Governance</span>{" "}
            in 15 Minutes
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            AI Identity is a transparent gateway that sits between your agents and LLM providers.
            No SDK lock-in, no agent code changes. Just change one URL and get identity, policy,
            and forensics built in.
          </p>
        </div>
      </section>

      {/* Steps */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto space-y-12">
          {steps.map((step) => (
            <div key={step.number} className="flex gap-6 md:gap-8">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 rounded-xl bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 flex items-center justify-center text-[rgb(166,218,255)] font-bold text-sm">
                  {step.number}
                </div>
              </div>
              <div>
                <h2 className="text-xl font-bold text-white mb-3">{step.title}</h2>
                <p className="text-sm text-gray-400 leading-relaxed mb-4">{step.description}</p>
                <ul className="space-y-2">
                  {step.details.map((detail) => (
                    <li key={detail} className="flex items-center gap-2 text-sm text-gray-300">
                      <svg className="w-4 h-4 text-[rgb(166,218,255)] flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      {detail}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Code Example */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">One Line to Integrate</h2>
          <p className="text-sm text-gray-400 text-center mb-8 max-w-[500px] mx-auto">
            Replace your LLM provider base URL. That's it. Your agents are now authenticated,
            policy-checked, and forensically logged.
          </p>
          <div className="rounded-xl border border-white/5 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2.5 bg-[rgb(16,19,28)] border-b border-white/5">
              <span className="text-xs font-mono text-[rgb(166,218,255)]/80">python</span>
              <span className="text-xs text-gray-500">Before & After</span>
            </div>
            <pre className="overflow-x-auto bg-[rgb(16,19,28)] p-4 text-sm leading-relaxed">
              <code className="text-gray-300 font-mono">{`# Before — direct to provider
client = OpenAI(api_key="sk-...")

# After — through AI Identity gateway
client = OpenAI(
    base_url="https://ai-identity-gateway.onrender.com/v1",
    api_key="aid_sk_your_agent_key",
)

# Everything else stays the same
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)`}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">Ready to get started?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Sign up free, register your first agent, and start routing in under 15 minutes.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <a href="https://dashboard.ai-identity.co" className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
                Get Started Free
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </a>
              <Link to="/docs" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                Read the Docs
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
