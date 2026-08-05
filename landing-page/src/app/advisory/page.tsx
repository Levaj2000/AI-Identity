import type { Metadata } from "next";
import Link from "next/link";
import { generatePageMetadata } from "@/lib/metadata";

export const metadata: Metadata = generatePageMetadata({
  title: "Advisory — Agent Identity, Audit Evidence & OCSF Adoption",
  description:
    "Advisory engagements with AI Identity founder Jeff Leva: agent identity and governance architecture, tamper-evident audit evidence, and OCSF adoption — from the person whose attestation work shipped in OCSF 1.9.0.",
  path: "/advisory",
});

const offerings = [
  {
    tag: "01 / IDENTITY",
    title: "Agent identity & governance architecture",
    body: "You have agents acting on shared credentials, service accounts, or someone's OAuth token. I help you design the identity layer they actually need: per-agent identity, scoped delegation, policy enforcement at the point of action, and key management that survives an audit question.",
  },
  {
    tag: "02 / EVIDENCE",
    title: "Audit evidence that stands up afterward",
    body: "Logs answer “what happened” only until someone asks “can you prove it?” I design tamper-evident evidence: cryptographically signed audit records, hash-chained histories, and verification that works independently of the system that produced the records — even offline.",
  },
  {
    tag: "03 / STANDARDS",
    title: "OCSF adoption & standards alignment",
    body: "I contribute to OCSF directly — my agent-attestation work shipped in the OCSF 1.9.0 release. If you're mapping AI or agent telemetry to OCSF, deciding what belongs upstream versus in an extension, or want your logging to interoperate with the broader security ecosystem, I can shorten that road considerably.",
  },
];

const receipts = [
  {
    lead: "OCSF 1.9.0",
    body: "Contributions shipped in the OCSF 1.9.0 release — agent attestation is now part of the open cybersecurity standard, with follow-on proposals queued for the next release.",
  },
  {
    lead: "IBM & CoSAI",
    body: "Working with engineers at IBM on OCSF-based audit logging for open-source AI gateway tooling; active contributor in CoSAI (OASIS) on agentic identity and trust.",
  },
  {
    lead: "LangChain",
    body: "Listed in LangChain's official documentation as an integration for agent identity and audit.",
  },
  {
    lead: "12+ years in production",
    body: "Operating systems where failure is expensive — cloud banking infrastructure supporting $50B+ in client assets, executive escalations at Sprint and Google.",
  },
  {
    lead: "AI Identity itself",
    body: "A production platform for agent identity, policy, and tamper-evident evidence — built, operated, and dogfooded by me.",
  },
];

export default function Advisory() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Advisory</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Advisory engagements, from the{" "}
            <span className="text-[rgb(166,218,255)]">person who built it</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[720px] mx-auto leading-relaxed">
            AI Identity is a working platform, not a slide deck — and the thinking behind it is
            available as advisory work. If your team is putting AI agents into production and the
            questions are starting to sound like <em>who did what, under whose authority, and can
            we prove it</em> — that&apos;s the work I do every day.
          </p>
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Where I can help */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-8">Where I Can Help</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {offerings.map((o) => (
              <div key={o.tag} className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
                <div className="text-[rgb(166,218,255)] font-mono text-sm mb-2">{o.tag}</div>
                <h3 className="text-base font-semibold text-white mb-2">{o.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{o.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* How engagements work */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">How Engagements Work</h2>
          <p className="text-sm text-gray-400 leading-relaxed max-w-[760px]">
            Short and focused. A typical engagement starts with an assessment — your agents,
            credentials, logs, and obligations as they exist today — and ends with an architecture
            you can build, a prioritized roadmap, and working reference examples where they help.
            Hands-on implementation support is available where it makes sense. No long retainers
            pitched by default; the goal is that you stop needing me.
          </p>
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Receipts */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">Why Me — the Receipts</h2>
          <p className="text-sm text-gray-400 leading-relaxed mb-8 max-w-[760px]">
            The credibility here was built in public — in standards bodies, open-source
            documentation, and a production platform — not in a pitch deck.
          </p>
          <div className="space-y-3">
            {receipts.map((r) => (
              <div
                key={r.lead}
                className="flex items-start gap-3 bg-white/[0.03] border border-white/10 rounded-xl p-5"
              >
                <svg
                  className="w-5 h-5 text-[rgb(166,218,255)] flex-shrink-0 mt-0.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <p className="text-sm text-gray-300 leading-relaxed">
                  <span className="font-semibold text-white">{r.lead}.</span> {r.body}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-6 text-sm text-gray-400">
            Who you&apos;d be working with:{" "}
            <a
              href="/jeff-leva-profile.pdf"
              className="text-[rgb(166,218,255)] hover:underline"
            >
              founder profile (PDF)
            </a>{" "}
            ·{" "}
            <Link href="/about" className="text-[rgb(166,218,255)] hover:underline">
              about AI Identity
            </Link>
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 pt-8 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h3 className="text-xl font-bold text-white mb-3">Start a conversation</h3>
            <p className="text-sm text-gray-400 mb-6 max-w-[540px] mx-auto">
              Email{" "}
              <a href="mailto:jeff@ai-identity.co" className="text-[rgb(166,218,255)] hover:underline">
                jeff@ai-identity.co
              </a>{" "}
              with two or three sentences about your situation — what your agents do, and the
              question you can&apos;t currently answer. I&apos;ll reply with an honest read on
              whether I can help, and what I&apos;d look at first.
            </p>
            <a
              href="mailto:jeff@ai-identity.co?subject=Advisory%20inquiry"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
            >
              Email Jeff
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
