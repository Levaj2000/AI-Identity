import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { generatePageMetadata } from "@/lib/metadata";

export const metadata: Metadata = generatePageMetadata({
  title: "About AI Identity — Company, Team, Mission & Stage",
  description:
    "AI Identity is a Boulder, Colorado company building identity, policy, and forensic audit infrastructure for AI agents. Meet the founder, learn what we build, and see who we serve.",
  path: "/about",
});

const FOUNDER_LINKEDIN = "https://www.linkedin.com/in/jeff-leva-a7373958";

export default function About() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-12 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">About AI Identity</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Identity &amp; Governance for{" "}
            <span className="text-[rgb(166,218,255)]">AI Agents</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[720px] mx-auto leading-relaxed">
            AI Identity gives every autonomous AI agent its own cryptographic identity, scoped
            permissions, and a tamper-evident audit trail — so security, platform, and compliance
            teams can deploy agents with accountability built in.
          </p>
        </div>
      </section>

      {/* Fast facts band */}
      <section className="pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Founded", value: "2026" },
            { label: "Headquarters", value: "Boulder, CO" },
            { label: "Stage", value: "Design Partner" },
            { label: "Category", value: "Agent IAM + Audit" },
          ].map((f) => (
            <div
              key={f.label}
              className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-center"
            >
              <p className="text-xs uppercase tracking-wider text-[rgba(213,219,230,0.5)] mb-1">
                {f.label}
              </p>
              <p className="text-base font-semibold text-white">{f.value}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* What we do */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">What AI Identity Builds</h2>
          <p className="text-sm text-gray-400 leading-relaxed mb-6 max-w-[760px]">
            AI Identity is a business-to-business software platform. We ship a hosted control plane
            and an open-source SDK that give organizations three things their current stack does
            not provide for AI agents:
          </p>

          <div className="grid md:grid-cols-3 gap-4 mb-8">
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
              <div className="text-[rgb(166,218,255)] font-mono text-sm mb-2">01 / IDENTITY</div>
              <h3 className="text-base font-semibold text-white mb-2">Per-agent API keys</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Unique, scoped <span className="font-mono text-[rgb(166,218,255)]">aid_sk_</span>{" "}
                credentials per agent. SHA-256 hashed at rest. Zero-downtime rotation. Revoke one
                agent without disturbing the others.
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
              <div className="text-[rgb(166,218,255)] font-mono text-sm mb-2">02 / POLICY</div>
              <h3 className="text-base font-semibold text-white mb-2">Context-aware gateway</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                A deny-by-default proxy in front of your LLM providers and internal APIs.
                Enforces least-privilege, rate limits, spending caps, and human-in-the-loop
                approvals for high-risk actions.
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
              <div className="text-[rgb(166,218,255)] font-mono text-sm mb-2">03 / EVIDENCE</div>
              <h3 className="text-base font-semibold text-white mb-2">Forensic audit trail</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                HMAC-SHA256 hash-chained logs, DSSE + ECDSA P-256 signed session attestations,
                and an offline verification CLI. Auditors verify independently of our servers.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href="/product"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[rgb(166,218,255)] text-[rgb(4,7,13)] text-sm font-semibold hover:bg-[rgb(166,218,255)]/80 transition-colors"
            >
              See product walkthrough →
            </Link>
            <Link
              href="/architecture"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/10 bg-white/[0.03] text-white text-sm font-medium hover:bg-white/[0.06] transition-colors"
            >
              Architecture
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/10 bg-white/[0.03] text-white text-sm font-medium hover:bg-white/[0.06] transition-colors"
            >
              Docs
            </Link>
          </div>
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Problems we solve */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">Problems We Solve</h2>
          <p className="text-sm text-gray-400 leading-relaxed mb-8 max-w-[760px]">
            Enterprises are deploying AI agents into production with infrastructure that was
            designed for humans and long-lived services — not for thousands of short-lived,
            autonomous workers making decisions on their behalf. That gap shows up in four places.
          </p>

          <div className="grid md:grid-cols-2 gap-4">
            {[
              {
                title: "Shared API keys hide who did what",
                body: "Teams ship one OpenAI/Anthropic key across every agent. When something goes wrong, there is no way to attribute an action to a specific agent, tool-call, or user session.",
              },
              {
                title: "No least-privilege at the agent layer",
                body: "Existing IAM and secret managers scope access per human or service account. There is no primitive for per-agent permissions, spending caps, tool allowlists, or deny-by-default enforcement.",
              },
              {
                title: "Audit logs aren't forensic evidence",
                body: "Provider-side logs are fine for debugging, but they are vendor-controlled, mutable, and incomplete. Regulators and auditors need tamper-evident, independently verifiable records.",
              },
              {
                title: "Compliance frameworks don't map cleanly",
                body: "EU AI Act Article 12, NIST AI RMF Measure, and SOC 2 CC7 all require traceability for automated decisions. Most teams have no control mapping between their runtime and the frameworks they're audited against.",
              },
            ].map((p) => (
              <div
                key={p.title}
                className="rounded-xl border border-white/10 bg-white/[0.03] p-5"
              >
                <h3 className="text-base font-semibold text-white mb-2">{p.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{p.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Who we serve */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">Who We Serve</h2>
          <p className="text-sm text-gray-400 leading-relaxed mb-8 max-w-[760px]">
            Our target customer is an organization deploying autonomous AI agents into production
            — typically through LangChain, LlamaIndex, CrewAI, AutoGen, OpenAI Agents SDK, or a
            custom framework — and accountable for what those agents do.
          </p>

          <div className="grid md:grid-cols-3 gap-4 mb-8">
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
              <h3 className="text-base font-semibold text-white mb-2">Platform &amp; AI engineering teams</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Own the agent runtime. Need per-agent keys, quota control, and a drop-in gateway
                that doesn&apos;t require rewriting every agent.
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
              <h3 className="text-base font-semibold text-white mb-2">Security &amp; IAM teams</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Own authorization. Need deny-by-default enforcement, scoped credentials, rotation,
                and anomaly detection for non-human identities.
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
              <h3 className="text-base font-semibold text-white mb-2">Risk, compliance &amp; audit</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Own the evidence. Need tamper-evident logs, signed attestations, and control
                mapping to EU AI Act, SOC 2, NIST AI RMF, GDPR, and HIPAA.
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <h3 className="text-sm uppercase tracking-wider text-[rgba(213,219,230,0.6)] mb-3">
              Industries we focus on first
            </h3>
            <div className="flex flex-wrap gap-2">
              {[
                "Financial services",
                "Healthcare",
                "Legal &amp; professional services",
                "SaaS platforms shipping agents",
                "Public sector &amp; regulated research",
              ].map((ind) => (
                <span
                  key={ind}
                  className="px-3 py-1 rounded-full border border-[rgba(166,218,255,0.2)] bg-[rgb(166,218,255)]/5 text-xs text-[rgba(213,219,230,0.8)]"
                  dangerouslySetInnerHTML={{ __html: ind }}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Team */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">Team</h2>
          <p className="text-sm text-gray-400 leading-relaxed mb-6 max-w-[760px]">
            AI Identity is founder-led. Jeff drives product, engineering, and customer
            relationships directly — which means every design partner gets direct access to the
            person who built the platform.
          </p>

          {/* Traction strip */}
          <div className="mb-8 rounded-xl border border-[rgba(166,218,255,0.2)] bg-[rgb(166,218,255)]/[0.04] px-5 py-4">
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm">
              <span className="flex items-center gap-2 text-[rgba(213,219,230,0.9)]">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-green-400" />
                </span>
                <span className="font-medium">Live in production</span>
              </span>
              <span className="text-[rgba(213,219,230,0.3)]">·</span>
              <span className="text-[rgba(213,219,230,0.9)]">
                <span className="font-medium">Design partners onboarding</span>
              </span>
              <span className="text-[rgba(213,219,230,0.3)]">·</span>
              <span className="text-[rgba(213,219,230,0.9)]">
                <span className="font-medium">Built on Google Cloud</span>
              </span>
            </div>
          </div>

          <div className="flex flex-col md:flex-row gap-8 items-start rounded-2xl border border-white/10 bg-white/[0.03] p-6 md:p-8">
            {/* Photo */}
            <div className="flex-shrink-0 mx-auto md:mx-0">
              <div className="w-56 h-64 rounded-2xl overflow-hidden border border-white/10">
                <Image
                  src="/images/jeff-leva.jpg"
                  alt="Jeff Leva, Founder and CEO of AI Identity"
                  width={224}
                  height={256}
                  className="w-full h-full object-cover"
                  priority
                />
              </div>
            </div>

            {/* Bio */}
            <div className="flex-1 min-w-0">
              <h3 className="text-xl font-semibold text-white">Jeff Leva</h3>
              <p className="text-sm text-[rgb(166,218,255)] mb-1">Founder &amp; CEO</p>
              <p className="text-xs text-[rgba(213,219,230,0.5)] mb-4">Boulder, Colorado</p>

              <p className="text-sm text-gray-400 leading-relaxed mb-3">
                Jeff has spent his career building and operating production systems in
                environments where failure isn&apos;t an option — cloud banking infrastructure
                handling $50B+ in client assets, enterprise platforms that teams run their
                businesses on, and the security and compliance tooling those environments demand.
              </p>
              <p className="text-sm text-gray-400 leading-relaxed mb-4">
                AI Identity came out of a pattern he kept seeing: organizations spinning up AI
                agents with shared credentials, no identity layer, and no way to answer who did
                what when something went wrong. Jeff founded AI Identity to give those teams the
                identity, policy, and evidence primitives they already expect for humans —
                purpose-built for agents.
              </p>

              <div className="flex flex-wrap gap-3">
                <a
                  href={FOUNDER_LINKEDIN}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-white/[0.03] text-sm text-white hover:bg-white/[0.08] transition-colors"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                  LinkedIn
                </a>
                <a
                  href="mailto:jeff@ai-identity.co"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-white/[0.03] text-sm text-white hover:bg-white/[0.08] transition-colors"
                >
                  jeff@ai-identity.co
                </a>
                <a
                  href="https://github.com/Levaj2000/AI-Identity"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-white/[0.03] text-sm text-white hover:bg-white/[0.08] transition-colors"
                >
                  GitHub
                </a>
              </div>
            </div>
          </div>

          {/* Team & Partners */}
          <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.02] p-5 md:p-6">
            <h3 className="text-base font-semibold text-white mb-3">Team &amp; Partners</h3>
            <p className="text-sm text-gray-400 leading-relaxed mb-3">
              We&apos;re selectively building our founding team and advisory network. If
              you&apos;ve scaled a developer platform, security product, or compliance tooling
              and want to be close to what&apos;s being built at the AI identity layer —{" "}
              <Link href="/contact" className="text-[rgb(166,218,255)] hover:underline">
                get in touch
              </Link>.
            </p>
            <p className="text-sm text-gray-400 leading-relaxed">
              We&apos;re also in conversation with potential co-founders with deep go-to-market
              or enterprise security backgrounds. If that&apos;s you,{" "}
              <Link href="/contact" className="text-[rgb(166,218,255)] hover:underline">
                let&apos;s talk
              </Link>.
            </p>
          </div>
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Current stage */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">Current Stage</h2>
          <p className="text-sm text-gray-400 leading-relaxed mb-6 max-w-[760px]">
            AI Identity is in early launch. Core product is live and running in production on our
            own infrastructure. We&apos;re selectively onboarding design partners and refining the
            product against their real workloads before broader GA.
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {[
              {
                label: "Live today",
                items: [
                  "Hosted control plane + dashboard",
                  "Gateway with OpenAI, Anthropic, Gemini",
                  "Python SDK + REST API + CLI",
                  "HMAC hash-chained audit log with org scoping + correlation IDs",
                  "DSSE + ECDSA P-256 signed attestations (KMS + public JWKS)",
                  "Offline attestation verification CLI",
                  "Human-in-the-loop approvals (Enterprise tier)",
                  "Shadow-agent detection with Register / Block / Dismiss flows",
                  "ABAC on agent metadata + policy dry-run endpoint",
                  "Org-level sharing + role-based assignments",
                  "Tier-based quota enforcement + usage tracking",
                  "Prometheus /metrics + real-time SIEM push (signed webhook)",
                  "Compliance export API: SOC 2, EU AI Act, NIST AI RMF (stubs)",
                  "GKE hardening: Binary Authorization ENFORCE, Cloud Armor WAF, Master Authorized Networks, NetworkPolicies, Secret Manager + CSI",
                  "Public interactive demo + 4-tier pricing page",
                ],
              },
              {
                label: "Next — design-partner track",
                items: [
                  "Terraform provider",
                  "Native SDK adapters for LangChain, CrewAI, AutoGen, OpenAI Agents SDK",
                  "Agent-to-agent auth (mTLS / token exchange)",
                  "Advanced anomaly detection beyond shadow-agent heuristics",
                  "Remaining 5th audit-logging phase",
                  "Dedicated SIEM connectors (Splunk, Datadog) on top of webhook sink",
                  "SOC 2 Type II external audit + ISO 27001 certification",
                  "Self-hosted / private-cloud deployment profile",
                  "SSO + SCIM provisioning",
                ],
              },
            ].map((col) => (
              <div
                key={col.label}
                className="rounded-xl border border-white/10 bg-white/[0.03] p-5"
              >
                <h3 className="text-xs uppercase tracking-wider text-[rgb(166,218,255)] font-semibold mb-3">
                  {col.label}
                </h3>
                <ul className="space-y-2">
                  {col.items.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-gray-300">
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
                      <span dangerouslySetInnerHTML={{ __html: item }} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Values */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">What We Believe</h2>
          <p className="text-sm text-gray-400 leading-relaxed mb-6">
            Three principles shape the product and the business.
          </p>
          <div className="space-y-3">
            {[
              "Every AI agent should have a real, verifiable identity — not a shared key and a best guess.",
              "Permissions should be explicit and least-privilege by default, with systems that fail closed when there's uncertainty.",
              "Audit trails should be tamper-evident and useful for real investigations — not just another log table.",
            ].map((principle, i) => (
              <div
                key={i}
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
                <p className="text-sm text-gray-300 leading-relaxed">{principle}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 pt-8 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h3 className="text-xl font-bold text-white mb-3">Let&apos;s talk</h3>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Whether you&apos;re exploring agent governance or ready to deploy, we&apos;d love to
              hear from you. Design partner slots are open through Q2 2026.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <a
                href="https://dashboard.ai-identity.co"
                className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
              >
                Get Started Free
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
              <Link
                href="/contact"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
              >
                Contact Jeff
              </Link>
              <a
                href={FOUNDER_LINKEDIN}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
              >
                Jeff on LinkedIn
              </a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
