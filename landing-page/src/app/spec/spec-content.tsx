import Link from "next/link";
import { pillars } from "@/data/pillars";

// Per-provider capability matrix for the §9.1 logprob exposure question.
// Sourced from public docs as of 2026-05. Update as providers ship changes.
const logprobMatrix = [
  {
    provider: "OpenAI",
    logprobs: "Yes",
    detail:
      "`logprobs` parameter returns top-N log-probabilities per token. Up to 5 alternatives via `top_logprobs`.",
    sufficient: "Yes",
  },
  {
    provider: "Anthropic",
    logprobs: "No (as of 2026-05)",
    detail:
      "No public logprob exposure on the Messages API. Forensic attestations rely on response provenance (model_id, system fingerprint, request_id) instead.",
    sufficient: "Partial",
  },
  {
    provider: "Google Gemini",
    logprobs: "Yes",
    detail:
      "`logprobs` and `responseLogprobs` available on the GenerateContent API. Up to 5 alternatives.",
    sufficient: "Yes",
  },
  {
    provider: "AWS Bedrock",
    logprobs: "Varies by model",
    detail:
      "Claude on Bedrock: no logprobs (parity with Anthropic direct). Other models: provider-dependent.",
    sufficient: "Partial",
  },
  {
    provider: "Self-hosted (vLLM, TGI, llama.cpp)",
    logprobs: "Yes",
    detail:
      "Full logprob distribution exposed. Strongest forensic signal — verifier can replay token-by-token sampling decisions.",
    sufficient: "Full",
  },
];

const standardsTrack = [
  {
    name: "OCSF",
    role: "Event envelope",
    detail:
      "Profiles the OCSF event schema for AI Agent Activity (new class proposed for upstream contribution).",
    href: "https://github.com/ocsf/ocsf-schema",
  },
  {
    name: "OpenTelemetry GenAI semconv",
    role: "Span attributes",
    detail:
      "Tool calls, model invocations, and policy evaluations emit OTEL spans following the GenAI semconv.",
    href: "https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai",
  },
  {
    name: "MITRE ATLAS 2026",
    role: "Threat taxonomy",
    detail:
      "Forensic events tag against ATLAS techniques (T0051 prompt injection, T0040 model theft, etc.) for SIEM correlation.",
    href: "https://atlas.mitre.org/",
  },
  {
    name: "SPIFFE / SPIRE",
    role: "Workload identity",
    detail:
      "Per-agent X.509-SVID or JWT-SVID identity binding optional; required for cross-trust-domain agent federation.",
    href: "https://spiffe.io/",
  },
  {
    name: "NIST AI RMF 1.0",
    role: "Governance mapping",
    detail:
      "Audit chain primitives map directly to MANAGE 4 (incident response) and MEASURE 2.7 (decision traceability).",
    href: "https://www.nist.gov/itl/ai-risk-management-framework",
  },
  {
    name: "IETF Agent Identity Protocol (AIP) draft",
    role: "Identity federation",
    detail:
      "Tracking the IETF AIP draft for future-proof cross-organization agent identity assertions.",
    href: "https://datatracker.ietf.org/",
  },
];

const openQuestions = [
  {
    n: "9.1",
    title: "Per-provider logprob exposure",
    body: "Anthropic and Bedrock-Claude do not expose token logprobs. Forensic attestations rely on response provenance (model_id, system fingerprint) — but this is weaker than logprob-backed replay. We track upstream changes here.",
  },
  {
    n: "9.2",
    title: "Multimodal context capture",
    body: "Image, audio, and video inputs are out of scope for v1.0. v1.1 plan in progress — likely capture content-hash + MIME + size rather than raw bytes, with optional vendor-specific perceptual hashes.",
  },
  {
    n: "9.3",
    title: "Cross-organization federation",
    body: "Agent identity assertions across trust domains depends on IETF AIP draft maturity. v1.0 assumes single-org trust domain; federation profile deferred to v1.2.",
  },
  {
    n: "9.4",
    title: "Vendor-hosted agent attestation",
    body: "Agents running entirely inside vendor-hosted runtimes (Perplexity hosted agents, OpenAI Custom GPTs, Anthropic Claude Projects, Manus, Devin) cannot be intercepted by the gateway-proxy pattern — calls originate inside vendor infrastructure with no operator-controlled injection point. v1.0 supports operator-assertion only (declarative registration, manual artifact logging). v1.1 will introduce Level 0 declarative conformance + a browser-side intercept profile; v1.2 tracks vendor-API attestation hooks. The most strategically important unanswered piece of v1.0.",
  },
];

export default function SpecContent() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-12 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="w-2 h-2 rounded-full bg-[rgb(166,218,255)]" />
            <span className="text-[rgb(166,218,255)] text-sm font-medium">
              Reference Specification — Draft v1.0
            </span>
            <span className="text-[rgba(213,219,230,0.5)] text-xs">·</span>
            <span className="text-[rgba(213,219,230,0.5)] text-xs">Published 2026-05-15</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            The AI Forensics{" "}
            <span className="text-[rgb(166,218,255)]">Audit Trail</span>{" "}
            Specification
          </h1>
          <p className="text-lg text-gray-400 max-w-[760px] mx-auto leading-relaxed">
            An open reference standard for tamper-evident, cryptographically-signed audit trails of autonomous AI agents. Profiles OCSF, OpenTelemetry GenAI, MITRE ATLAS, SPIFFE, and NIST AI RMF as a single coherent schema for forensic reconstruction — verifiable offline by auditors with no vendor dependency.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <a
              href="https://github.com/ai-identity/forensic-audit-trail-spec"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
            >
              Read the full spec on GitHub
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </a>
            <Link
              href="/forensics"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
            >
              How AI Identity implements this
            </Link>
          </div>
        </div>
      </section>

      {/* Four Pillars */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[1000px] mx-auto">
          <div className="text-center mb-10">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-3">
              The Spec at a Glance
            </p>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
              Four pillars, one coherent schema
            </h2>
            <p className="text-sm text-gray-400 max-w-[600px] mx-auto">
              The spec organizes forensic primitives into four pillars. Each pillar maps to a specific question an auditor will ask after an incident.
            </p>
          </div>
          <div className="overflow-hidden rounded-2xl border border-[rgba(216,231,242,0.07)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-white/[0.05]">
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    Pillar
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    The auditor&apos;s question
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    Spec capability
                  </th>
                </tr>
              </thead>
              <tbody>
                {pillars.map((p, i) => (
                  <tr
                    key={p.pillar}
                    className={`${i % 2 === 0 ? "bg-white/[0.02]" : ""} ${p.pillar === "Forensics" ? "border-l-2 border-l-[rgb(166,218,255)]" : ""}`}
                  >
                    <td className="px-6 py-4 font-semibold text-white whitespace-nowrap">{p.pillar}</td>
                    <td className="px-6 py-4 text-gray-400 italic">{p.question}</td>
                    <td className="px-6 py-4 text-gray-300">{p.capability}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Standards-track alignment */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[1100px] mx-auto">
          <div className="text-center mb-10">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-3">
              Built on Standards
            </p>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
              Standards-track alignment
            </h2>
            <p className="text-sm text-gray-400 max-w-[640px] mx-auto">
              The spec profiles existing open standards rather than inventing new ones. It is not a competing schema — it is a forensic-grade composition.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {standardsTrack.map((s) => (
              <a
                key={s.name}
                href={s.href}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-5 rounded-2xl border border-[rgba(216,231,242,0.07)] bg-white/[0.02] hover:border-[rgb(166,218,255)]/30 hover:bg-[rgb(166,218,255)]/[0.03] transition-colors group"
              >
                <div className="flex items-baseline justify-between gap-3 mb-2">
                  <h3 className="text-base font-semibold text-white">{s.name}</h3>
                  <span className="text-[10px] uppercase tracking-wider text-[rgb(166,218,255)] shrink-0">
                    {s.role}
                  </span>
                </div>
                <p className="text-sm text-[rgba(213,219,230,0.7)] leading-relaxed">{s.detail}</p>
                <p className="mt-3 text-xs text-[rgb(166,218,255)] opacity-70 group-hover:opacity-100 transition-opacity">
                  {s.href.replace(/^https?:\/\//, "")} →
                </p>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* Per-provider logprob matrix */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[1100px] mx-auto">
          <div className="text-center mb-10">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-3">
              §9.1 Capability Matrix
            </p>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
              Per-provider logprob exposure
            </h2>
            <p className="text-sm text-gray-400 max-w-[680px] mx-auto">
              Token-level log-probabilities are the strongest forensic signal — they let a verifier replay sampling decisions deterministically. Not every provider exposes them. This matrix tracks the state of public APIs as of 2026-05.
            </p>
          </div>
          <div className="overflow-hidden rounded-2xl border border-[rgba(216,231,242,0.07)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-white/[0.05]">
                  <th className="px-5 py-3 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    Provider
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    Logprobs
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    Detail
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-[rgb(166,218,255)] uppercase tracking-wider">
                    Forensic sufficiency
                  </th>
                </tr>
              </thead>
              <tbody>
                {logprobMatrix.map((row, i) => (
                  <tr key={row.provider} className={i % 2 === 0 ? "bg-white/[0.02]" : ""}>
                    <td className="px-5 py-4 font-semibold text-white whitespace-nowrap">{row.provider}</td>
                    <td className="px-5 py-4 text-gray-300 whitespace-nowrap">{row.logprobs}</td>
                    <td className="px-5 py-4 text-[rgba(213,219,230,0.7)]">{row.detail}</td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      <span
                        className={
                          row.sufficient === "Yes" || row.sufficient === "Full"
                            ? "text-green-400/80"
                            : "text-amber-300/80"
                        }
                      >
                        {row.sufficient}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-[rgba(213,219,230,0.5)] mt-4 text-center">
            See the full spec §9.1 for the verifier algorithm + fallback rules when logprobs are unavailable.
          </p>
        </div>
      </section>

      {/* Open questions */}
      <section className="py-16 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[900px] mx-auto">
          <div className="text-center mb-10">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[rgb(166,218,255)] mb-3">
              §9 Open Questions
            </p>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
              What v1.0 doesn&apos;t solve yet
            </h2>
            <p className="text-sm text-gray-400 max-w-[640px] mx-auto">
              A specification that hides its uncertainty is not a standard — it&apos;s a marketing document. These are the questions v1.0 leaves open, with v1.1 and v1.2 commitments where applicable.
            </p>
          </div>
          <div className="space-y-6">
            {openQuestions.map((q) => (
              <div key={q.n} className="border-l-2 border-[rgb(166,218,255)]/30 pl-6">
                <div className="flex items-baseline gap-3 mb-2">
                  <span className="text-xs font-mono text-[rgb(166,218,255)]">§{q.n}</span>
                  <h3 className="text-base font-semibold text-white">{q.title}</h3>
                </div>
                <p className="text-sm text-[rgba(213,219,230,0.75)] leading-relaxed">{q.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contribution / CTA */}
      <section className="py-20 px-6 md:px-12 border-t border-[rgba(216,231,242,0.05)]">
        <div className="max-w-[800px] mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
            Help us land v1.1
          </h2>
          <p className="text-sm text-[rgba(213,219,230,0.7)] mb-8 max-w-[560px] mx-auto">
            The spec is open and seeking community review. File issues on GitHub, comment on the OCSF discussion, or join the AI Identity design partner cohort to shape v1.1 against real production deployments.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <a
              href="https://github.com/ai-identity/forensic-audit-trail-spec/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
            >
              File a spec issue on GitHub
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </a>
            <Link
              href="/contact?intent=design-partner"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
            >
              Become a design partner
            </Link>
          </div>
          <p className="mt-8 text-xs text-[rgba(213,219,230,0.45)]">
            OCSF discussion issue:{" "}
            <a
              href="https://github.com/ocsf/ocsf-schema/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[rgb(166,218,255)] hover:underline"
            >
              filing pending
            </a>
            {" · "}
            Spec license: CC-BY-4.0 (content) + Apache-2.0 (reference impl)
          </p>
        </div>
      </section>
    </>
  );
}
