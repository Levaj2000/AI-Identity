import Link from "next/link";
import ProbeEmailCapture from "@/components/ProbeEmailCapture";

const pillars = [
  {
    title: "Replay any agent session",
    body: "Step-by-step decision trail with the exact prompt, the tool calls, the model response, and the policy evaluation that ran on each one. Reproduce a year-old incident from the chain — no log-stitching, no guessing what the agent saw.",
  },
  {
    title: "Tamper-evident by construction",
    body: "HMAC-SHA256 hash chain at write time; SLH-DSA post-quantum signatures land on the chain through Q1 2027. The audit trail is evidence, not just storage — an auditor verifies the chain independently of the vendor.",
  },
  {
    title: "Behavioral anomaly intelligence",
    body: "Per-agent behavioral baseline. Real-time drift detection flags when an agent deviates from its established permission envelope. Severity-scored auto-triage moves you from reactive logging to proactive threat intelligence.",
  },
  {
    title: "Regulator-ready evidence package",
    body: "One-click export of agent identity proof, authorization record, decision log, and cryptographic chain-of-custody. Pre-formatted for EU AI Act Article 12/13 technical documentation and SOC 2 CC7 audit evidence.",
  },
];

const useCases = [
  {
    label: "Incident response",
    body: "An agent moved a transaction it shouldn't have. You need to know which prompt, which tool call, which model version — and prove it didn't happen to anyone else. Forensic replay produces that timeline from the chain in minutes.",
  },
  {
    label: "Regulatory review",
    body: "EU AI Act, SOC 2, NIST AI RMF — auditors are starting to ask for traceable, tamper-evident records of AI decisions. AI Forensics is the artifact you hand them.",
  },
  {
    label: "Internal investigation",
    body: "A security team needs to know what an agent had access to last quarter and whether it ever exceeded scope. The chain answers without you reconstructing anything.",
  },
];

export default function AIForensicsContent() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-12 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">
              AI Forensics — coming soon
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Replay-grade evidence for{" "}
            <span className="text-[rgb(166,218,255)]">AI agent incidents</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[720px] mx-auto leading-relaxed">
            Chain-of-thought audit trails for autonomous AI agents — tamper-evident, replayable a year later, regulator-ready. Spinning into a standalone product. Get on the early-access list.
          </p>

          <div className="mt-10 flex justify-center">
            <ProbeEmailCapture
              probe="ai-forensics-standalone"
              label="Email for AI Forensics early access"
              cta="Get early access"
              successMessage="On the list. We'll reach out before launch."
            />
          </div>
        </div>
      </section>

      {/* What you get */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl font-bold text-white mb-12 text-center">
            What you get
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {pillars.map((p) => (
              <div
                key={p.title}
                className="p-6 rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgba(166,218,255,0.02)]"
              >
                <h3 className="text-lg font-semibold text-white mb-3">
                  {p.title}
                </h3>
                <p className="text-sm text-[rgba(213,219,230,0.75)] leading-relaxed">
                  {p.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use cases */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl font-bold text-white mb-10 text-center">
            Who it's for
          </h2>
          <div className="space-y-6">
            {useCases.map((u) => (
              <div key={u.label} className="border-l-2 border-[rgb(166,218,255)]/30 pl-6">
                <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-2">
                  {u.label}
                </p>
                <p className="text-sm text-[rgba(213,219,230,0.85)] leading-relaxed">
                  {u.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Relationship to AI Identity */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[900px] mx-auto text-center">
          <h2 className="text-2xl font-bold text-white mb-6">
            Built on the AI Identity audit primitive
          </h2>
          <p className="text-sm text-[rgba(213,219,230,0.75)] max-w-[680px] mx-auto leading-relaxed">
            AI Forensics is the forensic layer of the AI Identity platform — being packaged as a standalone product for teams that already run an LLM gateway (Portkey, LangSmith, Helicone, custom) and need forensic-grade audit on top. Same chain, same export profiles, separate purchase path.{" "}
            <Link
              href="/product"
              className="text-[rgb(166,218,255)] hover:underline"
            >
              See the full platform
            </Link>
            .
          </p>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-20 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[700px] mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
            Join the early-access list
          </h2>
          <p className="text-sm text-[rgba(213,219,230,0.7)] mb-8">
            We'll reach out before public availability with a private demo and design-partner pricing.
          </p>
          <div className="flex justify-center">
            <ProbeEmailCapture
              probe="ai-forensics-standalone"
              label="Email for AI Forensics early access"
              cta="Get early access"
              successMessage="On the list. We'll reach out before launch."
            />
          </div>
        </div>
      </section>
    </>
  );
}
