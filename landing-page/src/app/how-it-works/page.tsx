import type { Metadata } from "next";
import Link from "next/link";
import { generatePageMetadata } from "@/lib/metadata";
import { makeHowToSchema } from "@/lib/schemas";
import JsonLd from "@/components/JsonLd";

export const metadata: Metadata = generatePageMetadata({
  title: "How AI Agent Forensics Works",
  description: "See how AI Identity captures, signs, and verifies every agent action — producing tamper-evident audit trails regulators can verify offline. One-line integration.",
  path: "/how-it-works",
});

const steps = [
  {
    number: "01",
    title: "Route Through the Gateway",
    description: "Point your agents at the AI Identity gateway with one URL change. Every request — auth, policy evaluation, tool call, response — now flows through an evidence-capturing layer with sub-50ms overhead.",
    details: [
      "Drop-in replacement — change one URL",
      "Works with OpenAI, Anthropic, Gemini, and more",
      "Zero agent code changes, zero SDK lock-in",
    ],
  },
  {
    number: "02",
    title: "Identify Every Agent",
    description: "Each agent gets a unique aid_sk_ credential so every event in the audit trail attributes back to the responsible agent — not a shared service account. Scope what it can call, when, and how much.",
    details: [
      "Unique per-agent identity (no shared keys)",
      "Scoped permissions: tools, models, rate limits, budgets",
      "Automated key rotation, instant revocation",
    ],
  },
  {
    number: "03",
    title: "Capture Tamper-Evident Evidence",
    description: "Every request is recorded in an HMAC-SHA256 hash-chained log. Each event links cryptographically to the one before it — alter one record and the entire chain breaks. Sessions are sealed with DSSE + ECDSA-P256 attestations signed by hardware-held keys.",
    details: [
      "HMAC-SHA256 chained audit trail (per-org isolated)",
      "DSSE + ECDSA-P256 signed session attestations",
      "Signing keys held in KMS — never leave the HSM",
    ],
  },
  {
    number: "04",
    title: "Replay & Prove on Demand",
    description: "When something goes wrong — or an auditor asks — scrub through any session step-by-step, export a signed evidence bundle, and hand it to your auditor. They verify it offline with our open-source CLI. No vendor trust required.",
    details: [
      "Scrubbable incident replay across auth, policy, tool calls, blocks",
      "Export signed evidence bundles with chain-of-custody",
      "Offline verification via open-source `ai-identity verify` CLI",
    ],
  },
];

export default function HowItWorks() {
  return (
    <>
      <JsonLd data={makeHowToSchema()} />
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">How It Works</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            From One URL Change to{" "}
            <span className="text-[rgb(166,218,255)]">Forensic Evidence</span>{" "}
            in 15 Minutes
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            AI Identity is a transparent gateway between your agents and LLM providers. Change one URL, and every agent action becomes a tamper-evident, cryptographically-signed audit record — replayable on demand, verifiable offline.
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
    base_url="https://gateway.ai-identity.co/v1",
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
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">See the replay before you wire it up</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Walk through a live incident replay on the homepage, or talk to us about joining the design partner cohort.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link href="/contact?intent=design-partner" className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
                Request Design Partner Access
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </Link>
              <Link href="/#replay-demo" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                View Incident Replay Demo
              </Link>
            </div>
            <p className="mt-5 text-xs text-gray-500">
              Building today? <a href="https://dashboard.ai-identity.co" className="text-gray-300 hover:text-[rgb(166,218,255)] underline underline-offset-2">Spin up a free dev sandbox →</a>
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
