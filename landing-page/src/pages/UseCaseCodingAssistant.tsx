import { Link } from "react-router";
import SEO from "../components/SEO";

const challenges = [
  {
    title: "Code Exfiltration",
    description: "Coding assistants send your proprietary source to LLM providers. No visibility into what code leaves your environment or where it goes.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" /></svg>,
  },
  {
    title: "Shared Credentials",
    description: "One API key for all coding agents across all repos. A leak in one repository compromises your entire fleet of AI assistants.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" /></svg>,
  },
  {
    title: "No Visibility",
    description: "Which model saw which file? When? What was the response? Security teams are flying blind when AI assistants access source code.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>,
  },
];

const solutions = [
  {
    title: "Per-Repository Identities",
    description: "Each coding agent gets its own identity scoped to a specific repo or team. Isolate blast radius and revoke access per-project.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /></svg>,
  },
  {
    title: "Model Access Policies",
    description: "Control which agents can access which models. Restrict sensitive repos to approved models only — block experimental or preview models.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
  },
  {
    title: "Full Code Audit Trail",
    description: "Every code snippet sent to an LLM is logged with HMAC integrity. Know exactly what left your environment and when.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>,
  },
  {
    title: "Anomaly Detection",
    description: "Spot unusual patterns: bulk code submissions, off-hours access, unauthorized model switching. Get alerts before damage is done.",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
  },
];

const codeExample = `from ai_identity import AIIdentityClient

async with AIIdentityClient(api_key="aid_sk_...") as client:
    # Register a coding assistant for the payments repo
    agent = await client.agents.create(
        name="copilot-payments-repo",
        description="Coding assistant — payments service only",
    )

    # Restrict to approved models and working hours
    await client.policies.create(
        agent_id=agent.agent.id,
        rules={
            "allowed_models": ["gpt-4o", "claude-sonnet-4-20250514"],
            "blocked_models": ["*-preview", "*-experimental"],
            "time_window": {
                "start": "08:00",
                "end": "20:00",
                "timezone": "US/Eastern",
            },
        },
    )

    # Full audit trail of every code interaction
    logs = await client.audit.list(agent_id=agent.agent.id)
    print(f"Tracked {logs.total} code interactions")`;

export default function UseCaseCodingAssistant() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
      <SEO
        title="AI Agent Identity for Coding Assistants"
        description="Govern AI coding assistants with per-agent identity. Scoped permissions, human-in-the-loop gates, and tamper-proof audit trails for code generation agents."
        path="/use-cases/coding-assistant"
      />
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Use Case</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Lock Down Your{" "}
            <span className="text-[rgb(166,218,255)]">Coding</span>{" "}
            Assistants
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            AI coding agents see your source code. AI Identity controls what
            goes where — with per-repo identities, model restrictions, and
            a tamper-proof audit trail of every interaction.
          </p>
        </div>
      </section>

      {/* The Challenge */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">The Challenge</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Your code is your most valuable IP. AI coding assistants create new attack vectors.
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
            Complete visibility and control over every AI-code interaction.
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
            Register a coding agent with model restrictions and time-based policies.
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
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">Ready to protect your source code?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Start with AI Identity for free — per-repo agent identities, model policies, and full audit logging.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link to="/pricing" className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
                Get Started Free
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </Link>
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
