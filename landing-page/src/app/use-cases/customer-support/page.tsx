import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import Link from "next/link";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Forensics for Customer Support Agents",
  description: "Forensic-grade audit trails for AI support agents. Replay any customer interaction, prove what the agent did, satisfy CCPA/GDPR auditors offline.",
  path: "/use-cases/customer-support",
});

const challenges = [
  {
    title: "PII Exposure",
    description: "Support agents process names, emails, and payment info. One misconfigured prompt and customer data leaks to unintended endpoints.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>,
  },
  {
    title: "Shared API Keys",
    description: "Multiple agents share the same credentials. When one is compromised, they all are. No way to isolate or revoke individually.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" /></svg>,
  },
  {
    title: "Zero Audit Trail",
    description: "When a customer complains about AI behavior, you can't prove what the agent actually did. No logs, no accountability, no defense.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" /></svg>,
  },
];

const solutions = [
  {
    title: "Forensic Replay of Every Conversation",
    description: "HMAC-chained logs + DSSE-signed session attestations capture every agent action. When a customer disputes a chat, scrub through the exact sequence and produce signed evidence regulators verify offline.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3" /></svg>,
  },
  {
    title: "Per-Agent Identity",
    description: "Every support agent gets its own cryptographic identity and scoped API key. When something goes wrong the audit trail attributes back to the responsible agent, not a shared service account.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>,
  },
  {
    title: "Policy Enforcement at the Edge",
    description: "Restrict PII-containing endpoints, tool calls, and topics. The gateway blocks violations before they reach the model provider — and writes the block to the audit chain.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
  },
  {
    title: "Compliance Evidence Bundles",
    description: "One-click export of audit chain + signed attestations + offline verify CLI. CCPA, GDPR Art. 30, SOC 2 CC7 — your auditor verifies the math without contacting our servers.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>,
  },
];

const codeExample = `from ai_identity import AIIdentityClient

async with AIIdentityClient(api_key="aid_sk_...") as client:
    # Register a customer support agent
    agent = await client.agents.create(
        name="support-bot-tier1",
        description="Tier 1 customer support — billing inquiries only",
    )

    # Enforce PII boundaries
    await client.policies.create(
        agent_id=agent.agent.id,
        rules={
            "blocked_endpoints": ["/api/internal/*", "/admin/*"],
            "max_tokens_per_request": 4096,
            "allowed_topics": ["billing", "account_status", "refunds"],
        },
    )

    # Every action is now auditable
    print(f"Agent {agent.agent.name} is live with policy enforcement")`;

export default function UseCaseCustomerSupport() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Use Case</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Replay Any{" "}
            <span className="text-[rgb(166,218,255)]">Support Conversation</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            AI support agents handle sensitive customer data every day. When something goes wrong, you need to prove what the agent actually did — not guess. AI Identity gives every interaction a tamper-evident, cryptographically-signed audit trail.
          </p>
        </div>
      </section>

      {/* The Challenge */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">The Challenge</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Customer support agents are one of the most common AI deployments — and one of the most risky.
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
            Four layers of protection for every support agent interaction.
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
            Register a support agent with enforced policies in a few lines of Python.
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
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">Ready to put forensics on your support stack?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              We&apos;re onboarding design partners in support automation. Get hands-on access, shape the v1.0 spec, and lock in preferred pricing.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link href="/contact?intent=design-partner" className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
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
