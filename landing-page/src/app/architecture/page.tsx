import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Agent Security Architecture: Gateway & Zero Trust",
  description: "Explore AI Identity's gateway architecture: per-agent credential vaults, JWT auth, AES-256 encryption, signed OCSF audit records you can verify independently, and row-level tenant isolation.",
  path: "/architecture",
});

/* ─── tiny helper ─── */
function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block px-3 py-1 text-xs font-semibold text-[rgb(166,218,255)] bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full">
      {children}
    </span>
  );
}

/* ─── card used in feature grids ─── */
function Card({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 hover:border-[rgb(166,218,255)]/30 hover:bg-[rgb(166,218,255)]/[0.03] transition-all group">
      <div className="w-10 h-10 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center text-[rgb(166,218,255)] mb-4 group-hover:bg-[rgb(166,218,255)]/20 transition-colors">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-gray-400 leading-relaxed">{description}</p>
    </div>
  );
}

/* ─── section wrapper ─── */
function Section({ id, children, className = "" }: { id?: string; children: React.ReactNode; className?: string }) {
  return (
    <section id={id} className={`py-20 px-6 md:px-12 ${className}`}>
      <div className="max-w-[1100px] mx-auto">{children}</div>
    </section>
  );
}

/* ─── icons ─── */
const icons = {
  shield: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
  lock: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>,
  key: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" /></svg>,
  database: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>,
  users: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>,
  zap: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>,
  link: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>,
  file: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>,
  check: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>,
  globe: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>,
  layers: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></svg>,
  alertTriangle: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
  clock: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>,
};

export default function Architecture() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <Badge>For Design Partners</Badge>
          <h1 className="mt-6 text-4xl md:text-5xl font-extrabold text-white leading-tight">Platform Architecture</h1>
          <p className="mt-5 text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            A security-first identity and access management layer purpose-built
            for autonomous AI agents. Every request is authenticated, authorized,
            and audited before it reaches an LLM provider.
          </p>
        </div>
      </section>

      {/* System Diagram */}
      <Section id="diagram">
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">System Overview</h2>
        <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
          Every AI agent request flows through the AI Identity Gateway before
          reaching any LLM provider. The gateway enforces policy, manages
          credentials, and writes a tamper-evident, OCSF-formatted audit
          record — plus a signed attestation anyone can verify offline, with
          nothing but a public key.
        </p>

        <div className="relative bg-white/[0.02] border border-white/10 rounded-2xl p-6 md:p-10 overflow-x-auto">
          <div className="hidden md:block font-mono text-[13px] leading-[1.7] text-gray-300 whitespace-pre select-none">
{`
  ┌──────────────────┐       ┌─────────────────────────────────────────────────────────────────┐       ┌───────────────────┐
  │                  │       │                     AI Identity Platform                        │       │                   │
  │   Your AI        │       │  ┌──────────────┐  ┌────────────────┐  ┌────────────────────┐  │       │   LLM Providers   │
  │   Agents         │──────▶│  │   Gateway     │─▶│  Policy Engine  │─▶│  Credential Vault  │──│──────▶│                   │
  │                  │       │  │   (Proxy)     │  │  (Real-time)   │  │  (Encrypted)       │  │       │   OpenAI, etc.    │
  │   SDK / API      │       │  └──────┬───────┘  └────────────────┘  └────────────────────┘  │       │                   │
  │                  │       │         │                                                       │       └───────────────────┘
  └──────────────────┘       │         ▼                                                       │
                             │  ┌──────────────────────────────────────────────────────────┐   │       ┌───────────────────┐
                             │  │             Audit Trail · OCSF Event Records              │   │       │                   │
                             │  │    Every request → hash-linked, tamper-evident record     │   │       │   Management      │
                             │  │       HMAC-SHA256 chain + ECDSA-signed attestation        │   │       │   Dashboard       │
                             │  └──────────────────────────────────────────────────────────┘   │       │                   │
                             │                                                                 │       │   Policies, Keys, │
                             └────────────────────────────────┬────────────────────────────────┘       │   Analytics       │
                                                              │                                        └───────────────────┘
                                                              ▼
                                    ┌─────────────────────────┴────────────────────────┐
                                    │         Verifiable Evidence · Case File          │
                                    │ Export a signed OCSF bundle anyone can verify —  │
                                    │       no vendor, no trust in us required.        │
                                    └──────────────────────────────────────────────────┘`}
          </div>
          <div className="md:hidden font-mono text-[11px] leading-[1.7] text-gray-300 whitespace-pre select-none">
{`
  ┌──────────────────┐
  │  Your AI Agents  │
  │  (SDK / API)     │
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  AI Identity     │
  │  Gateway (Proxy) │
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  Policy Engine   │
  │  (Real-time)     │
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  Credential      │
  │  Vault           │
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  LLM Providers   │
  └──────────────────┘

  ┌──────────────────┐
  │  Audit Trail     │
  │  (OCSF · chain)  │
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  Verifiable      │
  │  Evidence ·      │
  │  Case File       │
  └──────────────────┘

  ┌──────────────────┐
  │  Dashboard       │
  └──────────────────┘`}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-6 justify-center text-xs text-gray-500">
          <span className="flex items-center gap-2"><span className="w-6 h-px bg-[rgb(166,218,255)]" /> Request flow</span>
          <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-[rgb(166,218,255)]/60" /> Encrypted at rest & in transit</span>
          <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-white/20" /> Signed OCSF evidence, verifiable offline</span>
        </div>

        <div className="mt-8 text-center">
          <a href="/forensics" className="inline-flex items-center gap-2 text-sm font-semibold text-[rgb(166,218,255)] hover:gap-3 transition-all">
            See a verifiable Case File
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
          </a>
        </div>
      </Section>

      <div className="max-w-[1100px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Key Architectural Properties */}
      <Section id="properties">
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Key Architectural Properties</h2>
        <p className="text-sm text-gray-400 text-center mb-12 max-w-[560px] mx-auto">The design decisions that make AI Identity enterprise-grade, compliance-sensitive, and forensically defensible — every agent action provable after the fact.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <Card icon={icons.alertTriangle} title="Fail-Closed Enforcement" description="Any error in the policy evaluation pipeline results in an automatic deny. Agents cannot bypass controls, even during partial outages." />
          <Card icon={icons.zap} title="Real-Time Policy Enforcement" description="Policy decisions are evaluated inline with less than 50ms of added latency. No queued evaluation, no eventual consistency — enforcement happens before the request proceeds." />
          <Card icon={icons.lock} title="Credential Vault" description="LLM provider API keys are stored in an encrypted vault. Agents never see or handle raw credentials — the gateway injects them at request time." />
          <Card icon={icons.key} title="Zero-Trust Key Separation" description="Runtime keys used by agents are fully separated from administrative keys. Compromising one does not compromise the other." />
          <Card icon={icons.users} title="Tenant Isolation" description="Row-level security ensures each tenant's data is completely isolated. One customer's agents, policies, and audit logs can never leak into another's." />
          <Card icon={icons.link} title="Tamper-Evident Audit Chain" description="Every event is cryptographically chained with HMAC-SHA256. Alter any record and the chain breaks — making tampering detectable and provable." />
          <Card icon={icons.layers} title="OCSF-Native Records" description="Every audit event is emitted in the Open Cybersecurity Schema Framework — the open standard our attestation and record-integrity work is now part of, merged into OCSF 1.9. Records drop straight into Splunk, your SIEM, or any OCSF tooling, no proprietary format to reverse-engineer." />
          <Card icon={icons.check} title="Independently Verifiable Evidence" description="Each forensic export carries an ECDSA-signed DSSE attestation. Auditors verify it completely offline with nothing but a public key — no access to our systems, no trust in the vendor required." />
          <Card icon={icons.file} title="Portable Case File Export" description="Package any incident into a self-contained Case File — signed OCSF records plus a drag-and-drop verifier. Hand it to counsel, an auditor, or a regulator and they can confirm integrity themselves." />
          <Card icon={icons.globe} title="Public Evidence Anchor" description="Roughly every 15 minutes, new audit events are committed to a signed Merkle checkpoint. Any single event can then be proven part of the committed record with nothing but our published public key — no shared secret, no access to our systems." />
          <Card icon={icons.key} title="Signed Spend Mandates" description="Organizations issue cryptographically signed spending authority that agents carry with them. The gateway enforces the limit before money moves, and every decision — allow, deny, exceeded — becomes chained audit evidence." />
        </div>
      </Section>

      <div className="max-w-[1100px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Security Layers */}
      <Section id="security-layers">
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Security Layers</h2>
        <p className="text-sm text-gray-400 text-center mb-12 max-w-[560px] mx-auto">Defense in depth — multiple independent layers ensure no single failure compromises the system, from the first byte on the wire to the evidence an auditor verifies months later.</p>
        <div className="relative max-w-[700px] mx-auto">
          <div className="absolute left-5 top-0 bottom-0 w-px bg-gradient-to-b from-[rgb(166,218,255)]/40 via-[rgb(166,218,255)]/20 to-transparent hidden sm:block" />
          {[
            { icon: icons.globe, title: "TLS Everywhere", desc: "All traffic is encrypted in transit using TLS 1.2+. No plaintext communication between any components." },
            { icon: icons.shield, title: "JWT Authentication", desc: "Every API request is authenticated via signed JSON Web Tokens with short-lived expiration and audience validation." },
            { icon: icons.clock, title: "Rate Limiting", desc: "Configurable per-agent and per-tenant rate limits prevent abuse and protect downstream LLM provider quotas." },
            { icon: icons.layers, title: "Policy Enforcement", desc: "Fine-grained rules control which agents can access which models, with what parameters, and under what conditions." },
            { icon: icons.database, title: "Encrypted Credential Storage", desc: "All sensitive credentials are encrypted at rest using AES-256. Decryption only occurs in-memory at request time." },
            { icon: icons.file, title: "OCSF-Native Audit Events", desc: "Every action is recorded as an Open Cybersecurity Schema Framework event — a vendor-neutral standard your SIEM already understands, no proprietary log format to parse." },
            { icon: icons.link, title: "Tamper-Evident Audit Chain", desc: "Audit events are sequentially chained with HMAC-SHA256. Any modification to a historical record breaks the chain and is cryptographically detectable." },
            { icon: icons.check, title: "Signed Forensic Attestation", desc: "Forensic exports are sealed in an ECDSA-signed DSSE envelope. Anyone can verify integrity and provenance offline with a public key — no access to AI Identity required." },
            { icon: icons.globe, title: "Public Evidence Anchor", desc: "Audit events are committed to signed Merkle checkpoints on a continuous ~15-minute cadence. A single event can be proven part of the committed record with the published public key alone — without disclosing any other event." },
          ].map((layer, i) => (
            <div key={i} className="relative flex items-start gap-5 mb-8 last:mb-0 sm:pl-14">
              <div className="absolute left-[13px] top-3 w-[14px] h-[14px] rounded-full border-2 border-[rgb(166,218,255)]/40 bg-[rgb(4,7,13)] hidden sm:block" />
              <div className="sm:hidden w-10 h-10 shrink-0 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center text-[rgb(166,218,255)]">{layer.icon}</div>
              <div>
                <h3 className="text-base font-semibold text-white mb-1 flex items-center gap-2">
                  <span className="hidden sm:inline-flex w-5 h-5 items-center justify-center text-[rgb(166,218,255)]">{layer.icon}</span>
                  {layer.title}
                </h3>
                <p className="text-sm text-gray-400 leading-relaxed">{layer.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <div className="max-w-[1100px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Compliance Alignment */}
      <Section id="compliance">
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Compliance Alignment</h2>
        <p className="text-sm text-gray-400 text-center mb-12 max-w-[560px] mx-auto">Built from the ground up to satisfy the requirements your security and compliance teams care about most.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            { icon: icons.check, title: "SOC 2", desc: "Architectural principles aligned with SOC 2 Trust Services Criteria.", items: ["Logical access controls with key separation", "Tamper-evident, independently verifiable audit trail", "Encrypted data at rest and in transit", "Tenant isolation with row-level security"] },
            { icon: icons.shield, title: "NIST AI RMF", desc: "Designed to support the NIST AI Risk Management Framework principles.", items: ["Complete observability of AI agent actions", "Policy-based governance and enforcement", "Signed, verifiable evidence for accountability", "Fail-closed design for reliability"] },
            { icon: icons.globe, title: "EU AI Act Ready", desc: "Infrastructure controls that support EU AI Act obligations for high-risk AI systems.", items: ["Human-in-the-loop policy overrides", "OCSF audit log for end-to-end traceability", "Transparent enforcement decisions", "Data residency-aware architecture"] },
          ].map((comp) => (
            <div key={comp.title} className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 hover:border-[rgb(166,218,255)]/30 transition-all">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center text-[rgb(166,218,255)]">{comp.icon}</div>
                <h3 className="text-base font-semibold text-white">{comp.title}</h3>
              </div>
              <p className="text-sm text-gray-400 leading-relaxed mb-4">{comp.desc}</p>
              <ul className="space-y-2 text-sm text-gray-400">
                {comp.items.map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <span className="text-[rgb(166,218,255)] mt-0.5 shrink-0">-</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      <div className="max-w-[1100px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* CTA */}
      <Section>
        <div className="text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">Ready to see it in action?</h2>
          <p className="text-sm text-gray-400 max-w-[480px] mx-auto mb-8">Walk through a live demo, or verify a signed Case File yourself — no account, no trust required.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a href="https://dashboard.ai-identity.co/demo" className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
              Live Demo
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </a>
            <a href="/forensics" className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-white/20 text-white font-semibold rounded-xl hover:border-[rgb(166,218,255)]/40 hover:bg-[rgb(166,218,255)]/[0.05] transition-all">
              Explore AI Forensics
            </a>
            <a href="/contact" className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-white/20 text-white font-semibold rounded-xl hover:border-[rgb(166,218,255)]/40 hover:bg-[rgb(166,218,255)]/[0.05] transition-all">
              Schedule a Call
            </a>
          </div>
        </div>
      </Section>
    </>
  );
}
