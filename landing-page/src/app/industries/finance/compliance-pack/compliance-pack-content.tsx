import Link from "next/link";
import ProbeEmailCapture from "@/components/ProbeEmailCapture";

const profiles = [
  {
    code: "NYDFS 23 NYCRR 500",
    title: "New York DFS Cybersecurity",
    body: "Access controls, audit trails, multi-factor for privileged access, third-party service provider risk — pre-mapped to per-agent identity, scoped credentials, signed-webhook SIEM push, and the AI Identity compliance export API. Ships with the §500.11 third-party assessment evidence packet.",
  },
  {
    code: "SEC Rule 17a-4",
    title: "Broker-Dealer Records Retention",
    body: "WORM-equivalent retention through tamper-evident hash-chained audit logs. Decision-by-decision attribution to a named agent identity. 6+ year retention horizon validated against post-quantum migration plan (Q3 2027 PQ-native credentials, SLH-DSA audit chain).",
  },
  {
    code: "MiFID II",
    title: "EU Investment Services Audit",
    body: "Article 16 record-keeping for AI-assisted advisory and execution decisions. Order-handling timestamp evidence and reconstructable decision trails. Pre-formatted ESMA-style transaction reporting fields included.",
  },
];

const inThePack = [
  "Per-agent cryptographic credentials, scoped to fund / desk / strategy",
  "Tamper-evident audit chain mapped to each regulator's evidence schema",
  "One-click compliance export bundles (PDF + JSON) for examiner requests",
  "Pre-mapped controls cross-walked to SOC 2 CC6/CC7, ISO 27001 A.12/A.13",
  "Cloud KMS HSM signing path — no signing keys leave the HSM boundary",
  "Real-time SIEM push via signed webhook for Splunk / Datadog / Sentinel",
];

const why = [
  {
    label: "AI agents are now in-scope",
    body: "Compliance teams that built controls for human traders are watching AI agents execute the same actions with no equivalent attribution. Examiners are starting to ask. NYDFS §500.11 third-party AI risk assessments and the SEC AI conduct rule landed in 2026.",
  },
  {
    label: "Shared API keys don't pass an exam",
    body: "If multiple agents share one credential, you can't answer 'which agent made this decision' to a regulator. The fix isn't more logging — it's per-agent identity from the start.",
  },
  {
    label: "Bolt-on logging fails on integrity",
    body: "Standard application logs are mutable, which means they aren't audit evidence. Hash-chained, signed decision records are. The audit trail has to be evidence on day one or it isn't audit at all.",
  },
];

export default function ComplianceContent() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-12 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">
              Financial Services Compliance Pack
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            AI agent compliance, pre-mapped to{" "}
            <span className="text-[rgb(166,218,255)]">the rules you already report against</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[760px] mx-auto leading-relaxed">
            NYDFS 23 NYCRR 500, SEC Rule 17a-4, MiFID II — three pre-built compliance profiles for financial-services AI agent fleets. Per-agent identity, tamper-evident audit, and one-click examiner-ready export. No customer-built control mappings required.
          </p>

          <div className="mt-10 flex justify-center">
            <ProbeEmailCapture
              probe="finance-compliance-pack"
              label="Email for the Finance Compliance Pack preview"
              cta="Request a preview"
              successMessage="Got it. We'll reach out with a preview walkthrough."
            />
          </div>
          <p className="text-xs text-[rgba(213,219,230,0.45)] mt-4">
            Preview includes a sample evidence packet for one regulator of your choice.
          </p>
        </div>
      </section>

      {/* Profiles */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl font-bold text-white mb-12 text-center">
            Three pre-built profiles
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {profiles.map((p) => (
              <div
                key={p.code}
                className="p-6 rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgba(166,218,255,0.02)]"
              >
                <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-2">
                  {p.code}
                </p>
                <h3 className="text-base font-semibold text-white mb-3">
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

      {/* What's in the pack */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl font-bold text-white mb-10 text-center">
            What's in the pack
          </h2>
          <ul className="space-y-3">
            {inThePack.map((line) => (
              <li
                key={line}
                className="flex items-start gap-3 text-sm text-[rgba(213,219,230,0.85)]"
              >
                <span
                  aria-hidden="true"
                  className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[rgb(166,218,255)] shrink-0"
                />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Why now */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl font-bold text-white mb-10 text-center">
            Why now
          </h2>
          <div className="space-y-6">
            {why.map((w) => (
              <div key={w.label} className="border-l-2 border-[rgb(166,218,255)]/30 pl-6">
                <p className="text-sm font-semibold text-white mb-2">{w.label}</p>
                <p className="text-sm text-[rgba(213,219,230,0.75)] leading-relaxed">
                  {w.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[700px] mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
            See a sample evidence packet
          </h2>
          <p className="text-sm text-[rgba(213,219,230,0.7)] mb-8">
            We'll send a walkthrough mapped to one regulator of your choice — NYDFS, SEC 17a-4, or MiFID II. No call required.
          </p>
          <div className="flex justify-center">
            <ProbeEmailCapture
              probe="finance-compliance-pack"
              label="Email for the Finance Compliance Pack preview"
              cta="Request a preview"
              successMessage="Got it. We'll reach out with a preview walkthrough."
            />
          </div>
          <p className="text-xs text-[rgba(213,219,230,0.45)] mt-6">
            Looking for the broader picture?{" "}
            <Link
              href="/forensics"
              className="text-[rgb(166,218,255)] hover:underline"
            >
              AI Forensics deep-dive
            </Link>
            {" · "}
            <Link
              href="/industries/finance"
              className="text-[rgb(166,218,255)] hover:underline"
            >
              Financial services overview
            </Link>
            {" · "}
            <Link
              href="/eu-ai-act-checklist"
              className="text-[rgb(166,218,255)] hover:underline"
            >
              EU AI Act checklist
            </Link>
          </p>
        </div>
      </section>
    </>
  );
}
