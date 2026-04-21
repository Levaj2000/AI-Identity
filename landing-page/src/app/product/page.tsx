import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { generatePageMetadata } from "@/lib/metadata";

export const metadata: Metadata = generatePageMetadata({
  title: "Product Walkthrough — AI Identity Dashboard, Gateway & Forensics",
  description:
    "See AI Identity in action: per-agent API keys, the policy-enforcing gateway, the compliance dashboard, and the forensic audit trail. Screenshots, features, and a live interactive demo.",
  path: "/product",
});

const DEMO_URL = "https://dashboard.ai-identity.co/demo";
const DASHBOARD_URL = "https://dashboard.ai-identity.co";
const DOCS_URL = "/docs";

type Step = {
  n: string;
  title: string;
  body: string;
  bullets: string[];
  visual: "dashboard" | "code-register" | "code-gateway" | "forensics" | "compliance";
};

const steps: Step[] = [
  {
    n: "01",
    title: "Register agents in the control plane",
    body: "Each AI agent gets a unique, scoped identity in the AI Identity control plane. No more shared OpenAI keys across ten agents and guessing which one ran up a bill.",
    bullets: [
      "Create agents via dashboard UI, REST API, Python SDK, or Terraform",
      "Per-agent metadata: owner, team, environment, intended tool-calls",
      "Unique aid_sk_ key issued once, SHA-256 hashed at rest",
      "Scope permissions: which models, which tools, which upstream APIs",
      "Set rate limits and monthly spending caps before the agent goes live",
    ],
    visual: "dashboard",
  },
  {
    n: "02",
    title: "Route agent traffic through the gateway",
    body: "Change one URL in your agent code. The AI Identity gateway authenticates every request, checks policy, and forwards to OpenAI, Anthropic, Gemini, or your internal APIs.",
    bullets: [
      "Drop-in OpenAI / Anthropic / Gemini compatible base URL",
      "Deny-by-default — invalid or expired keys are rejected at the edge",
      "Policy engine enforces per-agent scope, rate limits, spending caps",
      "Human-in-the-loop approvals for high-risk actions (configurable)",
      "Sub-50ms p99 overhead per request",
    ],
    visual: "code-gateway",
  },
  {
    n: "03",
    title: "Every action becomes tamper-evident evidence",
    body: "The gateway writes an HMAC-SHA256 hash-chained audit record for every request. Each session is closed with a DSSE + ECDSA P-256 signed attestation envelope.",
    bullets: [
      "Hash-chained log — alter one record and the entire chain breaks",
      "DSSE + ECDSA P-256 signed session attestations, KMS-backed signing keys",
      "Offline verification CLI — auditors fetch + verify without touching our servers",
      "Forensic replay: reconstruct an agent's complete decision path",
      "Export evidence bundles with chain-of-custody certificates",
    ],
    visual: "forensics",
  },
  {
    n: "04",
    title: "Map every control to a framework",
    body: "The compliance view shows a live control map to EU AI Act, SOC 2, NIST AI RMF, GDPR, and HIPAA. Export an audit-ready evidence bundle in one click.",
    bullets: [
      "Live control-mapping dashboard per framework",
      "Auto-generated evidence per control from real gateway activity",
      "Export profiles: SOC 2, EU AI Act, NIST AI RMF",
      "Chain-of-custody certificate bundled with every export",
      "Separate endpoints for stubbed frameworks (transparency on what's live vs. stub)",
    ],
    visual: "compliance",
  },
];

const features = [
  { group: "Identity", items: ["Per-agent aid_sk_ API keys", "Unique agent metadata & ownership", "Zero-downtime key rotation", "Scoped permissions", "Shadow-agent detection with Register / Block / Dismiss flows"] },
  { group: "Policy", items: ["Deny-by-default gateway", "ABAC on agent metadata", "Policy dry-run endpoint", "Tier-based quota enforcement", "Human-in-the-loop approvals (Enterprise)"] },
  { group: "Forensics", items: ["HMAC-SHA256 hash-chained audit log", "DSSE + ECDSA P-256 signed session attestations", "KMS-backed signing + public JWKS endpoint", "Offline verification CLI", "Signed webhook SIEM forwarding"] },
  { group: "Compliance", items: ["EU AI Act control map", "SOC 2 CC6.x + CC7 mappings", "NIST AI RMF alignment", "ISO 27001 A.12 / A.13 mapping", "One-click audit export"] },
  { group: "Integrations", items: ["OpenAI, Anthropic, Gemini", "Works with LangChain, CrewAI, AutoGen, OpenAI Agents SDK", "Python SDK + REST API", "Prometheus /metrics", "Real-time SIEM push (signed webhook)"] },
  { group: "Deployment & security", items: ["Hosted SaaS on GKE Autopilot", "Binary Authorization ENFORCE", "Cloud Armor WAF + Master Authorized Networks", "PostgreSQL Row-Level Security (FORCE)", "Org-scoped queries + correlation IDs"] },
];

function VisualDashboard() {
  return (
    <div className="rounded-xl border border-white/10 overflow-hidden bg-[rgb(16,19,28)]">
      <Image
        src="/images/dashboard-preview.jpg"
        alt="AI Identity dashboard overview — total agents, active sessions, request volume, and recent activity"
        width={1120}
        height={570}
        className="w-full h-auto"
      />
    </div>
  );
}

function VisualCodeGateway() {
  return (
    <div className="rounded-xl border border-white/10 bg-[rgb(16,19,28)] overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 bg-[rgb(10,13,20)] border-b border-white/5">
        <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
        <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
        <span className="ml-2 text-xs font-mono text-[rgb(166,218,255)]/80">python — agent.py</span>
      </div>
      <pre className="overflow-x-auto p-5 text-sm leading-relaxed">
        <code className="text-gray-300 font-mono">{`# Before — direct to provider
from openai import OpenAI
client = OpenAI(api_key="sk-...")

# After — through AI Identity
client = OpenAI(
    base_url="https://gateway.ai-identity.co/v1",
    api_key="aid_sk_7f3x...m9k2",  # per-agent key
)

# Every call is now:
#   authenticated  → per-agent identity
#   authorized     → scoped policy check
#   rate-limited   → per-agent quota
#   logged         → hash-chained audit record
#   attestable     → signed session envelope
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarize ticket #4821"}],
)`}</code>
      </pre>
    </div>
  );
}

function VisualForensics() {
  return (
    <div className="rounded-xl border border-white/10 bg-[rgb(16,19,28)] p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-[rgba(213,219,230,0.5)]">
            Session attestation
          </p>
          <p className="text-sm font-mono text-white mt-0.5">sess_8f2a4c71b9</p>
        </div>
        <span className="px-2 py-1 rounded-full border border-green-500/30 bg-green-500/10 text-xs text-green-300">
          verified ✓
        </span>
      </div>
      <div className="space-y-2 mb-5">
        {[
          { t: "00:00.000", e: "agent.authenticate", s: "ok", k: "aid_sk_7f3x" },
          { t: "00:00.042", e: "policy.evaluate", s: "allow", k: "model=gpt-4o tools=[crm.read]" },
          { t: "00:00.063", e: "llm.call", s: "ok", k: "tokens=1,240 / cap=50,000" },
          { t: "00:00.810", e: "tool.call", s: "allow", k: "crm.read ticket=4821" },
          { t: "00:01.112", e: "session.close", s: "signed", k: "dsse + ecdsa-p256" },
        ].map((r) => (
          <div
            key={r.t}
            className="grid grid-cols-[80px_1fr_80px] gap-3 items-center text-xs font-mono"
          >
            <span className="text-[rgba(213,219,230,0.4)]">{r.t}</span>
            <span className="text-[rgba(213,219,230,0.85)]">
              {r.e} <span className="text-[rgba(213,219,230,0.5)]">{r.k}</span>
            </span>
            <span
              className={
                r.s === "allow" || r.s === "ok" || r.s === "signed"
                  ? "text-green-400"
                  : "text-red-400"
              }
            >
              {r.s}
            </span>
          </div>
        ))}
      </div>
      <div className="rounded-lg border border-white/5 bg-[rgb(10,13,20)] p-3 text-xs font-mono text-[rgba(213,219,230,0.6)] overflow-x-auto">
        <div>sha256:{" "}<span className="text-[rgb(166,218,255)]">9b4c...af12</span></div>
        <div>prev:{" "}<span className="text-[rgba(213,219,230,0.45)]">e73a...c018</span></div>
        <div>signature:{" "}<span className="text-[rgba(213,219,230,0.45)]">MEYCIQD...</span></div>
      </div>
    </div>
  );
}

function VisualCompliance() {
  const rows = [
    { f: "EU AI Act", a: "Article 12 — logging & traceability", s: "5/5 live" },
    { f: "SOC 2", a: "CC7 — system monitoring", s: "4/5 live" },
    { f: "NIST AI RMF", a: "MEASURE 2.7 — decision traceability", s: "3/4 live" },
    { f: "GDPR", a: "Article 30 — record of processing", s: "2/3 live" },
    { f: "HIPAA", a: "§164.312(b) — audit controls", s: "stub" },
  ];
  return (
    <div className="rounded-xl border border-white/10 bg-[rgb(16,19,28)] overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
        <p className="text-sm font-semibold text-white">Framework mapping</p>
        <button className="text-xs px-3 py-1 rounded-full border border-[rgba(166,218,255,0.25)] bg-[rgb(166,218,255)]/10 text-[rgb(166,218,255)]">
          Export bundle →
        </button>
      </div>
      <div className="divide-y divide-white/5">
        {rows.map((r) => (
          <div
            key={r.f + r.a}
            className="grid grid-cols-[110px_1fr_110px] gap-3 items-center px-5 py-3 text-sm"
          >
            <span className="text-white font-semibold">{r.f}</span>
            <span className="text-[rgba(213,219,230,0.7)]">{r.a}</span>
            <span
              className={
                r.s === "stub"
                  ? "text-[rgba(213,219,230,0.45)] text-right"
                  : "text-green-300 text-right"
              }
            >
              {r.s}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StepVisual({ which }: { which: Step["visual"] }) {
  if (which === "dashboard") return <VisualDashboard />;
  if (which === "code-register")
    return (
      <div className="rounded-xl border border-white/10 bg-[rgb(16,19,28)] overflow-hidden">
        <div className="px-4 py-2.5 bg-[rgb(10,13,20)] border-b border-white/5 text-xs font-mono text-[rgb(166,218,255)]/80">
          curl — register agent
        </div>
        <pre className="overflow-x-auto p-5 text-sm leading-relaxed">
          <code className="text-gray-300 font-mono">{`$ curl -X POST https://api.ai-identity.co/v1/agents \\
    -H "Authorization: Bearer $ADMIN_KEY" \\
    -d '{"name":"support-triage","owner":"platform","scope":{"models":["gpt-4o"],"tools":["crm.read"]}}'

{
  "agent_id": "agt_04k2n9",
  "api_key":  "aid_sk_7f3x9m2k_...",   // shown once
  "key_prefix": "aid_sk_7f3x",
  "scope": { "models": ["gpt-4o"], "tools": ["crm.read"] },
  "limits": { "rpm": 60, "monthly_usd_cap": 500 }
}`}</code>
        </pre>
      </div>
    );
  if (which === "code-gateway") return <VisualCodeGateway />;
  if (which === "forensics") return <VisualForensics />;
  if (which === "compliance") return <VisualCompliance />;
  return null;
}

export default function ProductPage() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-12 px-6 md:px-12">
        <div className="max-w-[1000px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Product</span>
            <span className="text-[rgba(213,219,230,0.6)] text-sm">•</span>
            <span className="text-[rgba(213,219,230,0.7)] text-sm">Live · Design-partner stage</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            The AI Identity Platform —{" "}
            <span className="text-[rgb(166,218,255)]">in action</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[760px] mx-auto leading-relaxed">
            A walkthrough of what the product actually does: register agents, route traffic through
            the policy-enforcing gateway, capture tamper-evident forensic evidence, and map every
            action back to the compliance framework your auditor cares about.
          </p>
          <div className="mt-8 flex flex-wrap gap-3 justify-center">
            <a
              href={DEMO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[rgb(166,218,255)] text-[rgb(4,7,13)] text-sm font-semibold hover:bg-[rgb(166,218,255)]/80 transition-colors"
            >
              Try the interactive demo →
            </a>
            <a
              href={DASHBOARD_URL}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/10 bg-white/[0.03] text-white text-sm font-medium hover:bg-white/[0.06] transition-colors"
            >
              Open dashboard
            </a>
            <Link
              href={DOCS_URL}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/10 bg-white/[0.03] text-white text-sm font-medium hover:bg-white/[0.06] transition-colors"
            >
              Read the docs
            </Link>
          </div>
        </div>
      </section>

      {/* Hero screenshot */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <div className="rounded-2xl border border-white/10 bg-[rgb(16,19,28)] p-2 md:p-3 shadow-[0_40px_120px_rgba(166,218,255,0.06)]">
            <div className="rounded-xl overflow-hidden border border-white/5">
              <Image
                src="/images/dashboard-preview.jpg"
                alt="AI Identity control plane — overview of agents, keys, API latency, request volume, and recent agent activity"
                width={1120}
                height={570}
                className="w-full h-auto"
                priority
              />
            </div>
          </div>
          <p className="text-xs text-center text-[rgba(213,219,230,0.55)] mt-3">
            AI Identity dashboard overview — live from{" "}
            <a href={DASHBOARD_URL} className="text-[rgb(166,218,255)] hover:underline">
              dashboard.ai-identity.co
            </a>
          </p>
        </div>
      </section>

      {/* Three pillars */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-2 text-center">
            Three pillars, one platform
          </h2>
          <p className="text-sm text-gray-400 text-center max-w-[640px] mx-auto mb-10">
            Identity, policy, and evidence for every AI agent in your organization.
          </p>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              {
                k: "Identity",
                d: "Per-agent API keys, scoped permissions, lifecycle management, and shadow-agent detection — all at the API layer.",
              },
              {
                k: "Policy",
                d: "Deny-by-default gateway that enforces scope, rate limits, spending caps, and human-in-the-loop approvals before any upstream call.",
              },
              {
                k: "Evidence",
                d: "HMAC hash-chained logs, DSSE + ECDSA P-256 signed attestations, and an offline verification CLI. Auditors verify without trusting us.",
              },
            ].map((p) => (
              <div key={p.k} className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
                <h3 className="text-base font-semibold text-white mb-2">{p.k}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{p.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Walkthrough */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-2 text-center">
            Walkthrough
          </h2>
          <p className="text-sm text-gray-400 text-center max-w-[640px] mx-auto mb-12">
            Here&apos;s what happens from the moment an agent is registered to the moment an
            auditor verifies a year of activity.
          </p>

          <div className="space-y-16">
            {steps.map((s, i) => {
              const reversed = i % 2 === 1;
              return (
                <div
                  key={s.n}
                  className={`grid md:grid-cols-2 gap-8 md:gap-10 items-center ${
                    reversed ? "md:[&>*:first-child]:order-2" : ""
                  }`}
                >
                  <div>
                    <div className="inline-flex items-center gap-2 mb-3">
                      <span className="text-[rgb(166,218,255)] font-mono text-sm">{s.n}</span>
                      <span className="h-px w-8 bg-[rgba(166,218,255,0.35)]" />
                    </div>
                    <h3 className="text-xl md:text-2xl font-bold text-white mb-3">{s.title}</h3>
                    <p className="text-sm text-gray-400 leading-relaxed mb-4">{s.body}</p>
                    <ul className="space-y-2">
                      {s.bullets.map((b) => (
                        <li
                          key={b}
                          className="flex items-start gap-2 text-sm text-[rgba(213,219,230,0.8)]"
                        >
                          <svg
                            className="w-4 h-4 text-[rgb(166,218,255)] flex-shrink-0 mt-0.5"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            aria-hidden="true"
                          >
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          {b}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <StepVisual which={s.visual} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Features grid */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-2 text-center">
            Feature overview
          </h2>
          <p className="text-sm text-gray-400 text-center max-w-[640px] mx-auto mb-10">
            What&apos;s in the box today across identity, policy, forensics, compliance, and
            deployment.
          </p>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f) => (
              <div
                key={f.group}
                className="rounded-xl border border-white/10 bg-white/[0.03] p-5"
              >
                <h3 className="text-sm uppercase tracking-wider text-[rgb(166,218,255)] font-semibold mb-3">
                  {f.group}
                </h3>
                <ul className="space-y-2">
                  {f.items.map((it) => (
                    <li
                      key={it}
                      className="flex items-start gap-2 text-sm text-[rgba(213,219,230,0.85)]"
                    >
                      <svg
                        className="w-4 h-4 text-[rgb(166,218,255)]/80 flex-shrink-0 mt-0.5"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        aria-hidden="true"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      {it}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stage & roadmap */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-2 text-center">
            Current stage of development
          </h2>
          <p className="text-sm text-gray-400 text-center max-w-[640px] mx-auto mb-10">
            AI Identity is in early launch. The core product is live and running in production on
            our own infrastructure. We&apos;re selectively onboarding design partners.
          </p>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              {
                phase: "Live today",
                items: [
                  "Hosted control plane + dashboard",
                  "Gateway (OpenAI, Anthropic, Gemini)",
                  "Python SDK + REST API + CLI",
                  "HMAC hash-chained audit log with org scoping + correlation IDs",
                  "DSSE + ECDSA P-256 signed attestations (KMS + public JWKS)",
                  "Offline verification CLI",
                  "Human-in-the-loop approvals (Enterprise)",
                  "Shadow-agent detection + Register/Block/Dismiss flows",
                  "ABAC + policy dry-run",
                  "Org-level sharing + role-based assignments",
                  "Tier-based quota enforcement + usage tracking",
                  "Prometheus /metrics + real-time SIEM push (signed webhook)",
                  "Compliance export API: SOC 2, EU AI Act, NIST AI RMF (stubs live)",
                  "GKE hardened: Binary Authorization ENFORCE, Cloud Armor WAF, MAN, NetworkPolicies, Secret Manager + CSI",
                  "Public interactive demo + pricing page",
                ],
              },
              {
                phase: "Next — Q2/Q3 2026 (design partners)",
                items: [
                  "Terraform provider",
                  "Native SDK adapters (LangChain, CrewAI, AutoGen, OpenAI Agents SDK)",
                  "Agent-to-agent auth (mTLS / token exchange)",
                  "Advanced anomaly detection beyond shadow-agent heuristics",
                  "5th audit-logging phase (remaining observability hooks)",
                  "Dedicated SIEM connectors (Splunk, Datadog) on top of webhook sink",
                ],
              },
              {
                phase: "Enterprise track",
                items: [
                  "SOC 2 Type II external audit",
                  "ISO 27001 certification",
                  "Self-hosted / private cloud deployment profile",
                  "SSO + SCIM provisioning",
                  "Cross-org agent federation",
                  "Custom policy DSL",
                ],
              },
            ].map((p) => (
              <div key={p.phase} className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
                <h3 className="text-xs uppercase tracking-wider text-[rgb(166,218,255)] font-semibold mb-3">
                  {p.phase}
                </h3>
                <ul className="space-y-2">
                  {p.items.map((it) => (
                    <li
                      key={it}
                      className="flex items-start gap-2 text-sm text-[rgba(213,219,230,0.85)]"
                    >
                      <span className="w-1 h-1 rounded-full bg-[rgb(166,218,255)] mt-2 flex-shrink-0" />
                      {it}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[1000px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">
              See it running in your own account
            </h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[560px] mx-auto">
              The interactive demo executes real API calls against the live AI Identity backend —
              no mock data, no video. Or sign in and register your first agent in a couple of
              minutes.
            </p>
            <div className="flex items-center justify-center gap-3 flex-wrap">
              <a
                href={DEMO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
              >
                Try the live demo
              </a>
              <a
                href={DASHBOARD_URL}
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
              >
                Sign up free
              </a>
              <Link
                href="/contact"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
              >
                Become a design partner
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
