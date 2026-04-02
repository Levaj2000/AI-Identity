import { useState } from "react";
import BadgeFramerComponent from "../framer/elements/badge";
import MainButtonFramerComponent from "../framer/main-button";
import SEO, { organizationSchema, softwareApplicationSchema, websiteSchema } from "../components/SEO";

const steps = [
  {
    num: "01",
    title: "Register Agents",
    description:
      "Issue unique API keys to each AI agent with scoped permissions. Define what each agent can access, which tools it can call, and set rate limits.",
    details: [
      "One API call to register — get a unique aid_sk_ prefixed key",
      "Scope permissions per agent: read-only, write, admin, or custom",
      "Set rate limits and spending caps before the agent goes live",
      "Keys are SHA-256 hashed at rest — shown once, never stored in plain text",
    ],
  },
  {
    num: "02",
    title: "Enforce Policies",
    description:
      "The deny-by-default gateway validates every request before it reaches your upstream APIs. No valid key, no access — no exceptions.",
    details: [
      "Every request passes through the gateway — invalid or expired keys are rejected instantly",
      "Apply organization-wide governance rules: human-in-the-loop approvals for high-risk actions",
      "Real-time anomaly detection flags agents acting outside their defined boundaries",
      "Zero-downtime key rotation with configurable grace periods",
    ],
  },
  {
    num: "03",
    title: "Audit Everything",
    description:
      "Every agent action is logged to a tamper-proof, append-only audit trail. When regulators or customers ask what happened — you have the answer.",
    details: [
      "Full chain-of-thought capture: agent ID, timestamp, action, key fingerprint",
      "Cryptographically verifiable audit chain — tamper-evident by design",
      "Generate compliance reports for SOC 2, EU AI Act, and GDPR with one click",
      "Forensic replay: step through any agent session to see exactly what happened",
    ],
  },
];

function HowItWorksSteps() {
  const [active, setActive] = useState(0);
  const step = steps[active];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Step tabs */}
      <div className="flex rounded-xl border border-[rgba(216,231,242,0.07)] overflow-hidden mb-8">
        {steps.map((s, i) => (
          <button
            key={s.num}
            onClick={() => setActive(i)}
            className={`flex-1 py-4 px-6 text-sm font-medium transition-colors ${
              i === active
                ? "bg-[rgb(16,19,28)] text-white border-b-2 border-[rgb(166,218,255)]"
                : "text-[rgba(213,219,230,0.5)] hover:text-[rgba(213,219,230,0.8)] hover:bg-white/[0.02]"
            }`}
          >
            STEP {i + 1}
          </button>
        ))}
      </div>

      {/* Step content */}
      <div className="rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/50 p-8 md:p-10">
        <div className="text-[rgb(166,218,255)] text-sm font-mono mb-2">{step.num}</div>
        <h3 className="text-2xl font-medium text-white mb-3">{step.title}</h3>
        <p className="text-[rgba(213,219,230,0.6)] leading-relaxed mb-6 max-w-2xl">
          {step.description}
        </p>

        <ul className="space-y-3">
          {step.details.map((detail) => (
            <li key={detail} className="flex items-start gap-3">
              <svg
                width="16" height="16" viewBox="0 0 16 16" fill="none"
                className="shrink-0 mt-0.5 text-[rgb(166,218,255)]"
              >
                <path
                  d="M13.3 4.3L6 11.6 2.7 8.3"
                  stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
                />
              </svg>
              <span className="text-sm text-[rgba(213,219,230,0.55)] leading-relaxed">{detail}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="flex flex-col items-center">
      <SEO
        title="AI Identity — Identity Infrastructure for AI Agents"
        description="Per-agent API keys, scoped permissions, and tamper-proof audit trails for autonomous AI agents. SOC 2, EU AI Act, NIST compliant. Deploy in 15 minutes. Free trial."
        path="/"
        jsonLd={[organizationSchema, softwareApplicationSchema, websiteSchema]}
      />
      {/* ── Hero Section — video background + Landio-style atmosphere ── */}
      <section className="relative w-full overflow-hidden min-h-[100vh]" style={{ backgroundColor: "rgb(4,7,13)" }}>
        {/* Video background — dark 3D grid landscape (Landio style) */}
        <video
          className="absolute inset-0 w-full h-full object-cover"
          style={{ filter: "saturate(0.25) brightness(0.9) hue-rotate(210deg)" }}
          autoPlay
          loop
          muted
          playsInline
          poster="/images/hero-bg.jpg"
        >
          <source src="https://framerusercontent.com/assets/1g8IkhtJmlWcC4zEYWKUmeGWzI.mp4" type="video/mp4" />
        </video>
        {/* Dark overlay — match Landio's cool atmosphere */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ backgroundColor: "rgba(4,7,13,0.35)" }}
        />
        {/* Content vignette overlay — radial fade like Landio */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: "radial-gradient(75% 64%, rgba(255,255,255,0) 17.57%, rgb(4,7,13) 100%)" }}
        />

        {/* Bottom edge fade to page background */}
        <div className="absolute bottom-0 left-0 right-0 h-[200px] bg-gradient-to-t from-[rgb(4,7,13)] to-transparent pointer-events-none z-[2]" />

        {/* Hero content overlaid on top */}
        <div className="relative z-10 pt-40 pb-24 px-6 min-h-[100vh] flex items-center justify-center">
          <div className="max-w-[1200px] mx-auto text-center">

            {/* Pulsing accent dot */}
            <div className="flex justify-center mb-8">
              <div className="relative">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: "rgb(166,218,255)" }}
                />
                <div
                  className="absolute inset-0 w-3 h-3 rounded-full animate-ping"
                  style={{ backgroundColor: "rgb(148,209,255)", opacity: 0.4 }}
                />
              </div>
            </div>

            <div className="flex justify-center mb-8">
              <BadgeFramerComponent.Responsive content="IDENTITY FOR AI AGENTS" />
            </div>

            <h1
              className="text-4xl md:text-6xl lg:text-[80px] font-medium leading-[1.2] mb-6 max-w-4xl mx-auto"
              style={{
                background: "radial-gradient(99% 86%, rgb(213,219,230) 28.39%, rgb(4,7,13) 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
                letterSpacing: "-1.6px",
              }}
            >
              Every AI Agent Deserves an{" "}
              <span
                className="font-['Instrument_Serif'] italic"
                style={{
                  WebkitTextFillColor: "rgb(166,218,255)",
                  filter: "drop-shadow(0 0 20px rgba(166,218,255,0.3))",
                }}
              >
                Identity
              </span>
            </h1>

            <p
              className="text-lg md:text-xl max-w-2xl mx-auto mb-10"
              style={{ color: "rgba(213,219,230,0.7)", letterSpacing: "-0.32px" }}
            >
              Per-agent API keys, scoped permissions, and tamper-proof audit trails.
              Know which agent did what, when, and why — before regulators ask.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <MainButtonFramerComponent.Responsive
                title="Start Free Trial"
                link="https://dashboard.ai-identity.co"
                newTab={true}
              />
              <a
                href="/how-it-works"
                className="px-6 py-3 rounded-lg border border-[rgba(216,231,242,0.12)] text-sm text-[rgba(230,235,245,0.8)] hover:text-white hover:border-[rgba(216,231,242,0.25)] transition-colors"
              >
                See How It Works
              </a>
            </div>

            {/* Design partner callout + compliance badges */}
            <div className="mt-16 rounded-xl border border-[rgba(216,231,242,0.07)] bg-white/[0.02] px-6 py-4 max-w-xl mx-auto">
              <p className="text-sm text-[rgba(213,219,230,0.55)] text-center">
                AI Identity is in early launch and{" "}
                <a href="/contact" className="text-[rgb(166,218,255)] hover:underline">actively seeking design partners</a>.
                Get early access, shape the roadmap, and lock in preferred pricing.
              </p>
            </div>
            <div className="mt-6 flex flex-wrap justify-center gap-8 text-xs uppercase tracking-wider">
              <a href="/security" className="text-[rgba(213,219,230,0.35)] hover:text-[rgba(213,219,230,0.6)] transition-colors">SOC 2 Type II</a>
              <a href="/eu-ai-act-checklist" className="text-[rgba(213,219,230,0.35)] hover:text-[rgba(213,219,230,0.6)] transition-colors">EU AI Act Ready</a>
              <a href="/privacy" className="text-[rgba(213,219,230,0.35)] hover:text-[rgba(213,219,230,0.6)] transition-colors">GDPR Compliant</a>
              <a href="/security" className="text-[rgba(213,219,230,0.35)] hover:text-[rgba(213,219,230,0.6)] transition-colors">ISO 27001</a>
            </div>

            {/* Scroll indicator — down chevron like Landio */}
            <div className="mt-20 flex justify-center">
              <svg className="w-6 h-6 animate-bounce opacity-40" fill="none" stroke="rgb(213,219,230)" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* ── How It Works Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="HOW IT WORKS" />
            </div>
            <h2 className="text-3xl md:text-[44px] font-medium text-white mb-4 leading-[1.2]">
              Three Steps to{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Governed
              </span>{" "}
              AI
            </h2>
            <p className="text-[rgba(213,219,230,0.6)] max-w-xl mx-auto">
              From agent onboarding to continuous compliance -- get up and running in minutes.
            </p>
          </div>

          <HowItWorksSteps />
        </div>
      </section>

      {/* ── Features Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="CORE CAPABILITIES" />
            </div>
            <h2 className="text-3xl md:text-[44px] font-medium text-white mb-4 leading-[1.2]">
              Built for{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Enterprise
              </span>{" "}
              AI
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Per-Agent API Keys */}
            <div className="group rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/50 p-6 hover:border-[rgba(166,218,255,0.2)] transition-all duration-300 hover:shadow-[0_0_30px_rgba(166,218,255,0.05)]">
              {/* Code snippet visual */}
              <div className="rounded-lg bg-[rgb(4,7,13)] border border-[rgba(216,231,242,0.07)] p-4 mb-6 font-mono text-xs overflow-hidden">
                <div className="flex items-center gap-1.5 mb-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
                  <span className="ml-2 text-[rgba(213,219,230,0.3)]">terminal</span>
                </div>
                <div className="space-y-1.5">
                  <div><span className="text-[rgba(213,219,230,0.4)]">$</span> <span className="text-[rgb(166,218,255)]">curl</span> <span className="text-[rgba(213,219,230,0.5)]">-X POST /v1/agents</span></div>
                  <div className="text-green-400/70">{"{"} "api_key": "aid_sk_7f3x...m9k2" {"}"}</div>
                  <div><span className="text-[rgba(213,219,230,0.4)]">$</span> <span className="text-[rgb(166,218,255)]">curl</span> <span className="text-[rgba(213,219,230,0.5)]">-X POST /v1/agents/.../rotate</span></div>
                  <div className="text-green-400/70">{"{"} "new_key": "aid_sk_9d2k...x4n8" {"}"}</div>
                </div>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Per-Agent API Keys</h3>
              <p className="text-sm text-[rgba(213,219,230,0.55)] leading-relaxed">
                Issue unique <span className="text-[rgb(166,218,255)] font-mono text-xs">aid_sk_</span> credentials to every agent. Rotate, revoke, and scope permissions — zero downtime.
              </p>
            </div>

            {/* Real-Time Audit Logs */}
            <div className="group rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/50 p-6 hover:border-[rgba(166,218,255,0.2)] transition-all duration-300 hover:shadow-[0_0_30px_rgba(166,218,255,0.05)]">
              {/* Mini timeline visual */}
              <div className="rounded-lg bg-[rgb(4,7,13)] border border-[rgba(216,231,242,0.07)] p-4 mb-6 text-xs overflow-hidden">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[rgba(213,219,230,0.4)] font-medium">Audit Trail</span>
                  <span className="text-[rgba(213,219,230,0.25)]">Live</span>
                </div>
                <div className="space-y-2.5">
                  {[
                    { time: "12:04:32", agent: "chat-bot-01", action: "llm.generate", status: "ok" },
                    { time: "12:04:31", agent: "data-agent", action: "db.query", status: "ok" },
                    { time: "12:04:28", agent: "chat-bot-01", action: "tool.call", status: "ok" },
                    { time: "12:04:25", agent: "scraper-v2", action: "http.request", status: "blocked" },
                  ].map((log) => (
                    <div key={log.time + log.agent} className="flex items-center gap-2">
                      <span className="text-[rgba(213,219,230,0.3)] font-mono w-14 shrink-0">{log.time}</span>
                      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${log.status === "ok" ? "bg-green-400/70" : "bg-red-400/70"}`} />
                      <span className="text-[rgb(166,218,255)] truncate">{log.agent}</span>
                      <span className="text-[rgba(213,219,230,0.35)] ml-auto shrink-0">{log.action}</span>
                    </div>
                  ))}
                </div>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Real-Time Audit Logs</h3>
              <p className="text-sm text-[rgba(213,219,230,0.55)] leading-relaxed">
                Tamper-proof logs for every agent action. Full chain-of-thought capture for forensic replay and analysis.
              </p>
            </div>

            {/* Compliance Dashboard */}
            <div className="group rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/50 p-6 hover:border-[rgba(166,218,255,0.2)] transition-all duration-300 hover:shadow-[0_0_30px_rgba(166,218,255,0.05)]">
              {/* Framework badges visual */}
              <div className="rounded-lg bg-[rgb(4,7,13)] border border-[rgba(216,231,242,0.07)] p-4 mb-6">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[rgba(213,219,230,0.4)] text-xs font-medium">Compliance Status</span>
                  <span className="text-green-400/70 text-xs">All Passing</span>
                </div>
                <div className="space-y-2">
                  {[
                    { name: "SOC 2 Type II", score: 95, checks: "28/30" },
                    { name: "EU AI Act", score: 88, checks: "22/25" },
                    { name: "NIST AI RMF", score: 92, checks: "6/7" },
                    { name: "GDPR", score: 100, checks: "8/8" },
                  ].map((fw) => (
                    <div key={fw.name} className="flex items-center gap-3">
                      <span className="text-xs text-[rgba(213,219,230,0.5)] w-24 shrink-0">{fw.name}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-[rgba(216,231,242,0.07)] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-[rgb(166,218,255)]/60 transition-all duration-700"
                          style={{ width: `${fw.score}%` }}
                        />
                      </div>
                      <span className="text-xs text-[rgba(213,219,230,0.35)] font-mono w-10 text-right shrink-0">{fw.checks}</span>
                    </div>
                  ))}
                </div>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Compliance Dashboard</h3>
              <p className="text-sm text-[rgba(213,219,230,0.55)] leading-relaxed mb-3">
                SOC 2, EU AI Act, NIST, and GDPR compliance monitoring with automated assessments and one-click reports.
              </p>
              <a
                href="https://dashboard.ai-identity.co/demo"
                className="inline-flex items-center gap-1.5 text-xs text-[rgb(166,218,255)] hover:underline"
              >
                Try the live demo
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── Demo Video Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl md:text-3xl font-medium text-white mb-3">
              See It in{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Action
              </span>
            </h2>
            <p className="text-[rgba(213,219,230,0.6)] text-sm max-w-lg mx-auto">
              Walk through the full agent lifecycle — register, authenticate, enforce, and audit — in under 2 minutes.
            </p>
          </div>
          <div className="rounded-2xl overflow-hidden border border-[rgba(216,231,242,0.07)]" style={{ position: "relative", paddingBottom: "56.25%", height: 0 }}>
            <iframe
              src="https://www.loom.com/embed/9d2a91d23adc4505b76b02b201fef721?sid=auto&hide_owner=true&hide_share=true&hide_title=true&hideEmbedTopBar=true"
              frameBorder="0"
              allowFullScreen
              style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}
            />
          </div>
          <div className="text-center mt-6">
            <a
              href="https://dashboard.ai-identity.co/demo"
              className="inline-flex items-center gap-2 text-sm text-[rgb(166,218,255)] hover:underline"
            >
              Try it yourself — Interactive API Playground
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </a>
          </div>
        </div>
      </section>

      {/* ── Security & Compliance Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="SECURITY" />
            </div>
            <h2 className="text-3xl md:text-[44px] font-medium text-white mb-4 leading-[1.2]">
              Zero-Trust Agent{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Security
              </span>
            </h2>
            <p className="text-[rgba(213,219,230,0.6)] max-w-xl mx-auto">
              Enterprise-grade security designed for autonomous AI systems.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {[
              {
                icon: (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                ),
                title: "Scoped Permissions",
                desc: "Fine-grained access control for every agent. Limit tools, APIs, data access, and spending.",
                details: "Define exactly which upstream APIs each agent can call, what data it can read, and how much it can spend. Permissions are deny-by-default — agents get nothing until you explicitly grant it.",
              },
              {
                icon: (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                ),
                title: "Anomaly Detection",
                desc: "Real-time behavioral monitoring flags agents acting outside their defined boundaries.",
                details: "The gateway tracks request patterns per agent — volume spikes, unusual endpoints, out-of-scope tool calls. Anomalies trigger alerts before damage is done, not after.",
              },
              {
                icon: (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                  </svg>
                ),
                title: "Key Rotation",
                desc: "Automatic credential rotation with zero-downtime deployment. Revoke compromised keys instantly.",
                details: "Rotate keys with a single API call. Configurable grace periods let the old key work during rollover so agents never drop a request. Compromised? Revoke immediately — all in-flight requests on that key are rejected.",
              },
              {
                icon: (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="8.5" cy="7" r="4" /><line x1="20" y1="8" x2="20" y2="14" /><line x1="23" y1="11" x2="17" y2="11" />
                  </svg>
                ),
                title: "Human-in-the-Loop",
                desc: "Configurable approval gates for high-risk actions. Agents pause and wait for human review.",
                details: "Tag specific actions as requiring human approval — financial transactions, data deletions, external communications. The agent pauses mid-execution and waits for a reviewer to approve or reject before proceeding.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="group p-6 rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/50 hover:border-[rgba(166,218,255,0.25)] hover:shadow-[0_0_30px_rgba(166,218,255,0.06)] transition-all duration-300 cursor-default"
                style={{ boxShadow: "inset 0px 2px 1px 0px rgba(207, 231, 255, 0.1)" }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/15 flex items-center justify-center group-hover:bg-[rgb(166,218,255)]/15 transition-colors">
                    {item.icon}
                  </div>
                  <h3 className="text-lg font-medium text-white">{item.title}</h3>
                </div>
                <p className="text-sm text-[rgba(213,219,230,0.6)] mb-3">{item.desc}</p>
                <p className="text-xs text-[rgba(213,219,230,0.4)] leading-relaxed group-hover:text-[rgba(213,219,230,0.55)] transition-colors">
                  {item.details}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Comparison Section — Why AI Identity ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="COMPARISON" />
            </div>
            <h2 className="text-3xl md:text-[44px] font-medium text-white mb-4 leading-[1.2]">
              Why AI Identity{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Over Others
              </span>
            </h2>
            <p className="text-[rgba(213,219,230,0.6)] max-w-xl mx-auto">
              See how purpose-built agent infrastructure compares to DIY or generic solutions.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {/* AI Identity column */}
            <div className="rounded-2xl border border-[rgb(166,218,255)]/20 bg-[rgb(16,19,28)]/50 p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 flex items-center justify-center">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
                  </svg>
                </div>
                <span className="text-white font-medium">AI Identity</span>
              </div>
              <ul className="space-y-4">
                {[
                  "Per-agent keys with deny-by-default gateway",
                  "Tamper-proof audit chain — cryptographically verifiable",
                  "One API call to register, rotate, or revoke",
                  "Built-in compliance engine (SOC 2, EU AI Act, NIST)",
                  "Forensic replay of any agent session",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 mt-0.5 text-[rgb(166,218,255)]">
                      <path d="M13.3 4.3L6 11.6 2.7 8.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="text-sm text-[rgba(213,219,230,0.7)]">{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Others column */}
            <div className="rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/30 p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(213,219,230,0.4)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                  </svg>
                </div>
                <span className="text-[rgba(213,219,230,0.5)] font-medium font-['Instrument_Serif'] italic">DIY &amp; Legacy IAM</span>
              </div>
              <ul className="space-y-4">
                {[
                  "Shared API keys or manual token management",
                  "Mutable logs with no tamper-proof guarantees",
                  "No chain-of-thought capture or forensic replay",
                  "Human IAM tools retrofitted for agent workflows",
                  "Enterprise-first pricing and 6-month sales cycles",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 mt-0.5 text-[rgba(213,219,230,0.25)]">
                      <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                    <span className="text-sm text-[rgba(213,219,230,0.4)]">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <p className="text-center mt-8 text-xs text-[rgba(213,219,230,0.35)] max-w-2xl mx-auto">
            Traditional IAM platforms like Okta are adding agent identity features — but they're extending human-first architectures.
            AI Identity is built from the ground up for autonomous agents: cryptographic audit chains, chain-of-thought forensics, and a developer-first API you can integrate in minutes, not months.
          </p>
        </div>
      </section>

      {/* ── Forensics Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="FORENSICS" />
            </div>
            <h2 className="text-3xl md:text-[44px] font-medium text-white mb-4 leading-[1.2]">
              AI Agent{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Forensics
              </span>
            </h2>
            <p className="text-[rgba(213,219,230,0.6)] max-w-xl mx-auto">
              When something goes wrong, trace the full chain of events -- from the triggering request to every tool call and decision.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Chain-of-Thought Logs */}
            <div className="group rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/50 p-6 hover:border-[rgba(166,218,255,0.2)] transition-all duration-300 hover:shadow-[0_0_30px_rgba(166,218,255,0.05)]">
              <div className="rounded-lg bg-[rgb(4,7,13)] border border-[rgba(216,231,242,0.07)] p-4 mb-6 text-xs font-mono overflow-hidden">
                <div className="flex items-center gap-2 mb-3">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                  <span className="text-[rgba(213,219,230,0.4)]">Chain of Thought</span>
                </div>
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <span className="text-[rgb(166,218,255)] shrink-0">1.</span>
                    <span className="text-[rgba(213,219,230,0.45)]">User asked to summarize Q3 report</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-[rgb(166,218,255)] shrink-0">2.</span>
                    <span className="text-[rgba(213,219,230,0.45)]">Calling tool: <span className="text-green-400/70">db.query</span> → financials</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-[rgb(166,218,255)] shrink-0">3.</span>
                    <span className="text-[rgba(213,219,230,0.45)]">Retrieved 847 rows, filtering to Q3</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-[rgb(166,218,255)] shrink-0">4.</span>
                    <span className="text-[rgba(213,219,230,0.45)]">Generating summary with key metrics</span>
                  </div>
                </div>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Chain-of-Thought Logs</h3>
              <p className="text-sm text-[rgba(213,219,230,0.55)] leading-relaxed">
                Capture every reasoning step. See why an agent chose a tool, what data it read, and how it reached its conclusion.
              </p>
            </div>

            {/* Action Replay */}
            <div className="group rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/50 p-6 hover:border-[rgba(166,218,255,0.2)] transition-all duration-300 hover:shadow-[0_0_30px_rgba(166,218,255,0.05)]">
              <div className="rounded-lg bg-[rgb(4,7,13)] border border-[rgba(216,231,242,0.07)] p-4 mb-6 text-xs overflow-hidden">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[rgba(213,219,230,0.4)] font-medium">Session Replay</span>
                  <span className="text-[rgb(166,218,255)] font-mono">▶ 4/7 steps</span>
                </div>
                {/* Timeline */}
                <div className="relative ml-3 border-l border-[rgba(216,231,242,0.1)] space-y-3 pl-4">
                  {[
                    { action: "auth.verify", time: "0ms", status: "ok" },
                    { action: "policy.check", time: "12ms", status: "ok" },
                    { action: "tool.call → search_api", time: "145ms", status: "ok" },
                    { action: "tool.call → send_email", time: "203ms", status: "blocked" },
                  ].map((ev) => (
                    <div key={ev.action} className="relative flex items-center gap-2">
                      <div className={`absolute -left-[21px] w-2.5 h-2.5 rounded-full border-2 border-[rgb(4,7,13)] ${ev.status === "ok" ? "bg-green-400/70" : "bg-red-400/70"}`} />
                      <span className="text-[rgba(213,219,230,0.5)]">{ev.action}</span>
                      <span className="text-[rgba(213,219,230,0.25)] ml-auto font-mono">{ev.time}</span>
                    </div>
                  ))}
                </div>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Action Replay</h3>
              <p className="text-sm text-[rgba(213,219,230,0.55)] leading-relaxed">
                Step through any agent session in order. See the exact sequence of auth, policy checks, tool calls, and where it was blocked.
              </p>
            </div>

            {/* Root Cause Analysis */}
            <div className="group rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/50 p-6 hover:border-[rgba(166,218,255,0.2)] transition-all duration-300 hover:shadow-[0_0_30px_rgba(166,218,255,0.05)]">
              <div className="rounded-lg bg-[rgb(4,7,13)] border border-[rgba(216,231,242,0.07)] p-4 mb-6 text-xs overflow-hidden">
                <div className="flex items-center gap-2 mb-3">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="1.5"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
                  <span className="text-[rgba(213,219,230,0.4)] font-medium">Incident #1847</span>
                  <span className="ml-auto px-1.5 py-0.5 rounded bg-red-500/15 text-red-400/80 text-[10px] font-medium">RESOLVED</span>
                </div>
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <span className="text-red-400/70 shrink-0">✗</span>
                    <span className="text-[rgba(213,219,230,0.45)]">Agent <span className="text-white/70">scraper-v2</span> sent 12k requests in 30s</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[rgb(166,218,255)] shrink-0">→</span>
                    <span className="text-[rgba(213,219,230,0.45)]">Root cause: missing rate limit on /search</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-400/70 shrink-0">✓</span>
                    <span className="text-[rgba(213,219,230,0.45)]">Fix: policy updated, key rotated, agent resumed</span>
                  </div>
                </div>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Root Cause Analysis</h3>
              <p className="text-sm text-[rgba(213,219,230,0.55)] leading-relaxed">
                Automated incident investigation traces failures back to the originating event. See the full chain — trigger, escalation, resolution.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Pricing Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="PRICING" />
            </div>
            <h2 className="text-3xl md:text-[44px] font-medium text-white mb-4 leading-[1.2]">
              Simple,{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Transparent
              </span>{" "}
              Pricing
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-5xl mx-auto">
            {[
              { name: "Free", price: "$0", period: "/mo", highlight: "5 agents", desc: "Perfect for prototyping", featured: false },
              { name: "Pro", price: "$79", period: "/mo", highlight: "50 agents", desc: "For teams in production", featured: true },
              { name: "Business", price: "$299", period: "/mo", highlight: "200 agents", desc: "Advanced requirements", featured: false },
              { name: "Enterprise", price: "Custom", period: "", highlight: "Unlimited", desc: "Compliance & on-prem", featured: false },
            ].map((tier) => (
              <a
                key={tier.name}
                href="/pricing"
                className={`group rounded-2xl p-6 border transition-all duration-300 hover:shadow-[0_0_30px_rgba(166,218,255,0.06)] ${
                  tier.featured
                    ? "border-[rgb(166,218,255)]/30 bg-[rgb(16,19,28)]/80 hover:border-[rgb(166,218,255)]/50"
                    : "border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/50 hover:border-[rgba(166,218,255,0.2)]"
                }`}
              >
                {tier.featured && (
                  <span className="inline-block mb-3 px-2 py-0.5 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] text-[10px] font-semibold rounded-full">
                    Most Popular
                  </span>
                )}
                <h3 className="text-base font-medium text-white">{tier.name}</h3>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-white">{tier.price}</span>
                  {tier.period && <span className="text-[rgba(213,219,230,0.4)] text-sm">{tier.period}</span>}
                </div>
                <p className="mt-1 text-xs text-[rgba(213,219,230,0.4)]">{tier.desc}</p>
                <div className="mt-4 pt-4 border-t border-[rgba(216,231,242,0.07)]">
                  <span className="text-sm text-[rgb(166,218,255)]">{tier.highlight}</span>
                </div>
              </a>
            ))}
          </div>

          <div className="text-center mt-10">
            <a
              href="/pricing"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-[rgba(216,231,242,0.12)] text-sm text-[rgba(213,219,230,0.8)] hover:text-white hover:border-[rgb(166,218,255)]/30 transition-colors"
            >
              View full pricing, comparison & estimator
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </a>
          </div>
        </div>
      </section>

      {/* ── CTA Section ── */}
      <section className="w-full py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-[44px] font-medium text-white leading-[1.2] mb-4">
            Ready to Secure Your{" "}
            <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
              AI Agents
            </span>
            ?
          </h2>
          <p className="text-[rgba(213,219,230,0.6)] max-w-xl mx-auto mb-8">
            Start free with 5 agents. No credit card required. Go from zero to governed AI in under 15 minutes.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <a
              href="https://dashboard.ai-identity.co"
              className="px-8 py-3.5 rounded-lg bg-[rgb(166,218,255)] text-[rgb(4,7,13)] text-sm font-semibold hover:bg-[rgb(166,218,255)]/80 transition-colors"
            >
              Start Free Trial
            </a>
            <a
              href="/contact"
              className="px-8 py-3.5 rounded-lg border border-[rgba(216,231,242,0.12)] text-sm text-[rgba(213,219,230,0.8)] hover:text-white hover:border-[rgb(166,218,255)]/30 transition-colors"
            >
              Contact Sales
            </a>
          </div>

          {/* Social + Contact */}
          <div className="flex items-center justify-center gap-6 mb-6">
            <a href="https://x.com/aiidentityco" target="_blank" rel="noopener noreferrer" className="text-[rgba(213,219,230,0.4)] hover:text-white transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" /></svg>
            </a>
            <a href="https://github.com/Levaj2000/AI-Identity" target="_blank" rel="noopener noreferrer" className="text-[rgba(213,219,230,0.4)] hover:text-white transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" /></svg>
            </a>
            <a href="https://linkedin.com/company/ai-identity" target="_blank" rel="noopener noreferrer" className="text-[rgba(213,219,230,0.4)] hover:text-white transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" /></svg>
            </a>
          </div>

          <p className="text-sm text-[rgba(213,219,230,0.4)]">
            <a href="mailto:jeff@ai-identity.co" className="hover:text-[rgb(166,218,255)] transition-colors">jeff@ai-identity.co</a>
          </p>
        </div>
      </section>
    </div>
  );
}
