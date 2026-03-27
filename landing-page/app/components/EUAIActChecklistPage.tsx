import { useState } from "react";
import { motion } from "framer-motion";
import Nav from "./landing/Nav";
import Footer from "./landing/Footer";

interface ChecklistItem {
  id: string;
  text: string;
  helper: string;
}

interface ChecklistSection {
  title: string;
  article: string;
  color: string;
  pillar: string;
  pillarColor: string;
  items: ChecklistItem[];
}

const sections: ChecklistSection[] = [
  {
    title: "Agent Classification & Registration",
    article: "Annex III",
    color: "#3B82F6",
    pillar: "Identity",
    pillarColor: "#F59E0B",
    items: [
      { id: "c1", text: "Identified which AI agents qualify as high-risk under the EU AI Act", helper: "Do you know which of your agents make decisions that could affect health, safety, or legal rights? These are likely high-risk under the Act." },
      { id: "c2", text: "Documented each agent's purpose, scope, and operational boundaries", helper: "Can you describe what each agent does, what data it accesses, and what it's not allowed to do — in writing?" },
      { id: "c3", text: "Maintained a current inventory/registry of all production agents", helper: "Do you have a single place (spreadsheet, dashboard, or registry) listing every AI agent running in production?" },
      { id: "c4", text: "Assigned a responsible human operator for each agent", helper: "Is there a named person accountable for each agent's behavior and decisions?" },
    ],
  },
  {
    title: "Identity & Traceability",
    article: "Article 13 \u2014 Transparency",
    color: "#F59E0B",
    pillar: "Identity",
    pillarColor: "#F59E0B",
    items: [
      { id: "t1", text: "Each agent has a unique, cryptographic identity (not shared API keys)", helper: "Does every agent authenticate with its own unique key or certificate — not a shared token used by multiple agents?" },
      { id: "t2", text: "Agent credentials are scoped to specific capabilities", helper: "Are agent keys limited to only what that agent needs? For example, a support agent can't access billing data." },
      { id: "t3", text: "Key rotation and lifecycle management is automated", helper: "Do agent keys expire and rotate automatically, or are they set once and never changed?" },
      { id: "t4", text: "Agent identity can be verified at any point in the chain", helper: "If an agent makes a request, can you trace it back to a specific registered agent identity?" },
    ],
  },
  {
    title: "Risk Management",
    article: "Article 9",
    color: "#EF4444",
    pillar: "Policy",
    pillarColor: "#8B5CF6",
    items: [
      { id: "r1", text: "Conducted risk assessment for each high-risk agent", helper: "Have you evaluated what could go wrong with each agent — unauthorized actions, data leaks, or incorrect decisions?" },
      { id: "r2", text: "Documented known limitations and failure modes", helper: "Is there a written record of what each agent can't do well, and what happens when it fails?" },
      { id: "r3", text: "Implemented fail-closed defaults (deny on error, not allow)", helper: "When something goes wrong, does the system block the action by default — or does it let it through?" },
      { id: "r4", text: "Residual risks are monitored and reviewed periodically", helper: "Do you regularly check whether your mitigations are still working, or has it been 'set and forget'?" },
    ],
  },
  {
    title: "Technical Documentation & Logging",
    article: "Article 12 \u2014 Record-Keeping",
    color: "#10B981",
    pillar: "Compliance",
    pillarColor: "#10B981",
    items: [
      { id: "l1", text: "All agent decisions are logged automatically", helper: "Is every allow/deny decision your agents make written to a log without anyone having to remember to do it?" },
      { id: "l2", text: "Logs are tamper-evident (cryptographic hash chain or equivalent)", helper: "Can you prove that no one — not even an admin — has altered the audit logs after the fact?" },
      { id: "l3", text: "PII is sanitized from audit records", helper: "Are personal details like emails, phone numbers, and tokens automatically stripped from logs?" },
      { id: "l4", text: "Logs are retained for the required period (minimum as specified)", helper: "Are your logs kept for at least the minimum period regulators expect (typically 6-12 months)?" },
      { id: "l5", text: "Evidence can be exported for auditors or regulators on demand", helper: "Can you generate a clean CSV or JSON export of agent activity within minutes if an auditor asks?" },
    ],
  },
  {
    title: "Human Oversight",
    article: "Article 14",
    color: "#8B5CF6",
    pillar: "Policy",
    pillarColor: "#8B5CF6",
    items: [
      { id: "h1", text: "Human-in-the-loop controls exist for high-risk decisions", helper: "For sensitive actions (deleting data, financial transactions), does a human review or approve before the agent acts?" },
      { id: "h2", text: "Agents can be paused or deactivated immediately", helper: "Can you shut down a misbehaving agent in seconds — not hours or days?" },
      { id: "h3", text: "Policy enforcement prevents agents from bypassing human rules", helper: "Are your rules enforced at the infrastructure level, or could a clever prompt or config change let an agent skip them?" },
      { id: "h4", text: "Override and intervention capabilities are documented", helper: "Is there a written procedure for how to intervene when an agent goes off-script?" },
    ],
  },
  {
    title: "Accuracy, Robustness & Cybersecurity",
    article: "Article 15",
    color: "#06B6D4",
    pillar: "Identity",
    pillarColor: "#F59E0B",
    items: [
      { id: "s1", text: "Input validation prevents injection and manipulation", helper: "Are agent inputs checked for malicious content (prompt injection, SQL injection) before being processed?" },
      { id: "s2", text: "Rate limiting and circuit breakers protect against abuse", helper: "If an agent starts making thousands of requests per second, does the system automatically throttle or stop it?" },
      { id: "s3", text: "Security headers and encryption are enforced", helper: "Is all data encrypted in transit (HTTPS/TLS) and are standard security headers present on every response?" },
      { id: "s4", text: "Regular security audits are conducted", helper: "When was the last time someone reviewed your agent infrastructure for vulnerabilities? If you can't remember, that's a gap." },
    ],
  },
  {
    title: "Post-Market Monitoring & Incident Response",
    article: "Articles 72 & 73",
    color: "#F97316",
    pillar: "Forensics",
    pillarColor: "#EF4444",
    items: [
      { id: "p1", text: "Anomaly detection identifies unusual agent behavior", helper: "Would you know within minutes if an agent suddenly started making requests it's never made before?" },
      { id: "p2", text: "Incident response plan covers AI agent-specific scenarios", helper: "Does your incident playbook include 'what to do if an AI agent goes rogue' — not just traditional server outages?" },
      { id: "p3", text: "Forensic replay can reconstruct any agent incident", helper: "After an incident, can you replay exactly what happened — every request, every decision, every timestamp?" },
      { id: "p4", text: "Serious incidents can be reported to authorities with evidence", helper: "If a regulator asks 'what happened?', can you hand them a tamper-proof evidence package within 72 hours?" },
    ],
  },
];

const totalItems = sections.reduce((acc, s) => acc + s.items.length, 0);

const scoreRanges = [
  { min: 0, max: 8, label: "Critical gaps", desc: "Your agents are at risk of non-compliance. Immediate action is needed.", color: "#EF4444" },
  { min: 9, max: 16, label: "Partial coverage", desc: "Key areas need attention before August 2026 enforcement.", color: "#F59E0B" },
  { min: 17, max: 22, label: "Strong foundation", desc: "Fill remaining gaps to be fully prepared before the deadline.", color: "#3B82F6" },
  { min: 23, max: 25, label: "Excellent", desc: "You're ahead of most organizations. Keep maintaining your posture.", color: "#10B981" },
];

const pillarMapping = [
  {
    pillar: "Identity",
    color: "#F59E0B",
    icon: "key",
    sections: ["Agent Classification & Registration", "Identity & Traceability", "Accuracy, Robustness & Cybersecurity"],
    automated: ["Cryptographic agent identities", "Scoped credential management", "Automated key rotation", "Agent registry with full metadata"],
  },
  {
    pillar: "Policy",
    color: "#8B5CF6",
    icon: "shield",
    sections: ["Risk Management", "Human Oversight"],
    automated: ["Policy-as-code enforcement", "Human-in-the-loop controls", "Fail-closed defaults", "Kill-switch and pause capabilities"],
  },
  {
    pillar: "Compliance",
    color: "#10B981",
    icon: "check",
    sections: ["Technical Documentation & Logging"],
    automated: ["Automated, tamper-evident audit logs", "PII sanitization in records", "One-click evidence export", "Retention policy management"],
  },
  {
    pillar: "Forensics",
    color: "#EF4444",
    icon: "search",
    sections: ["Post-Market Monitoring & Incident Response"],
    automated: ["Anomaly detection for agent behavior", "Full incident timeline reconstruction", "Forensic replay of agent actions", "Regulator-ready evidence packages"],
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04 } },
};

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

export default function EUAIActChecklistPage() {
  const [checked, setChecked] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const score = checked.size;
  const currentRange = scoreRanges.find((r) => score >= r.min && score <= r.max) || scoreRanges[0];
  const progressPercent = (score / totalItems) * 100;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="size-full bg-[#0a0a0b] overflow-auto">
      <Nav />

      {/* Print-only styles */}
      <style>{`
        @media print {
          nav, footer, .no-print { display: none !important; }
          body, .size-full { background: white !important; color: black !important; }
          * { color: #111 !important; border-color: #ccc !important; background: transparent !important; }
          .print-break { page-break-before: always; }
          section { padding: 1rem !important; }
          h1 { font-size: 24pt !important; }
          h2 { font-size: 16pt !important; }
          h3 { font-size: 13pt !important; }
          .checklist-item { break-inside: avoid; }
        }
      `}</style>

      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[#8B5CF6]/10 border border-[#8B5CF6]/20 rounded-full mb-6">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8B5CF6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <path d="M2 12h20" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
              <span className="text-sm font-medium text-[#8B5CF6]">EU AI Act</span>
            </div>

            <h1 className="text-3xl md:text-5xl font-bold text-white mb-4 leading-tight">
              EU AI Act Compliance Checklist{" "}
              <span className="text-gray-500">for AI Agents</span>
            </h1>

            <p className="text-lg text-gray-400 max-w-[700px] mx-auto mb-6 leading-relaxed">
              Is your AI agent fleet ready for August 2026? The EU AI Act's high-risk
              provisions will require organizations deploying autonomous AI agents to
              demonstrate identity controls, logging, human oversight, and incident
              response capabilities. Use this checklist to assess your readiness.
            </p>

            <div className="flex items-center justify-center gap-4 no-print">
              <button
                onClick={handlePrint}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-white/5 border border-white/10 text-white text-sm font-medium rounded-lg hover:bg-white/10 transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 9 6 2 18 2 18 9" />
                  <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                  <rect x="6" y="14" width="12" height="8" />
                </svg>
                Print / Save as PDF
              </button>
            </div>
          </motion.div>

          {/* Score Bar */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="bg-[#111113]/80 backdrop-blur-xl border border-white/5 rounded-2xl p-6 mb-12"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">Your Score</h3>
              <span className="text-sm font-mono" style={{ color: currentRange.color }}>
                {score} / {totalItems}
              </span>
            </div>
            <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden mb-3">
              <div
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${progressPercent}%`,
                  backgroundColor: currentRange.color,
                }}
              />
            </div>
            <div className="flex items-center gap-2">
              <span
                className="text-xs font-semibold px-2 py-0.5 rounded-full"
                style={{ backgroundColor: `${currentRange.color}20`, color: currentRange.color }}
              >
                {currentRange.label}
              </span>
              <span className="text-xs text-gray-500">{currentRange.desc}</span>
            </div>
          </motion.div>

          {/* Checklist Sections */}
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="space-y-8"
          >
            {sections.map((section, sectionIdx) => (
              <motion.div
                key={section.title}
                variants={item}
                className="bg-[#111113]/80 backdrop-blur-xl border border-white/5 rounded-2xl overflow-hidden"
              >
                {/* Section Header */}
                <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
                      style={{ backgroundColor: `${section.color}15`, color: section.color }}
                    >
                      {sectionIdx + 1}
                    </div>
                    <div>
                      <h2 className="text-sm font-semibold text-white">{section.title}</h2>
                      <span className="text-xs text-gray-500">{section.article}</span>
                    </div>
                  </div>
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: `${section.pillarColor}15`, color: section.pillarColor }}
                  >
                    {section.pillar} Pillar
                  </span>
                </div>

                {/* Checklist Items */}
                <div className="px-6 py-3">
                  {section.items.map((checkItem) => (
                    <label
                      key={checkItem.id}
                      className="checklist-item flex items-start gap-3 py-3 cursor-pointer group border-b border-white/[0.03] last:border-0"
                    >
                      <div className="mt-0.5 flex-shrink-0">
                        <input
                          type="checkbox"
                          checked={checked.has(checkItem.id)}
                          onChange={() => toggle(checkItem.id)}
                          className="sr-only peer"
                        />
                        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          checked.has(checkItem.id)
                            ? "bg-[#F59E0B] border-[#F59E0B]"
                            : "border-gray-600 group-hover:border-gray-400"
                        }`}>
                          {checked.has(checkItem.id) && (
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#0A0A0B" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <span className={`text-sm leading-relaxed transition-colors ${
                          checked.has(checkItem.id)
                            ? "text-gray-500 line-through"
                            : "text-gray-300 group-hover:text-white"
                        }`}>
                          {checkItem.text}
                        </span>
                        <span className="text-[13px] leading-snug text-gray-500">
                          {checkItem.helper}
                        </span>
                      </div>
                    </label>
                  ))}
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Scoring Guide */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mt-12 bg-[#111113]/80 backdrop-blur-xl border border-white/5 rounded-2xl p-6 print-break"
          >
            <h2 className="text-lg font-semibold text-white mb-4">Scoring Guide</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {scoreRanges.map((range) => (
                <div
                  key={range.label}
                  className="flex items-start gap-3 p-4 rounded-xl border border-white/5"
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{ backgroundColor: `${range.color}15`, color: range.color }}
                  >
                    {range.min}-{range.max}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">{range.label}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{range.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* How AI Identity Helps */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mt-12 print-break"
          >
            <div className="text-center mb-8">
              <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
                How AI Identity Helps
              </h2>
              <p className="text-gray-400 text-sm max-w-[600px] mx-auto">
                Each pillar of AI Identity maps directly to EU AI Act requirement areas,
                automating the controls that are hardest to maintain manually.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pillarMapping.map((p) => (
                <div
                  key={p.pillar}
                  className="bg-[#111113]/80 backdrop-blur-xl border border-white/5 rounded-2xl p-6"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${p.color}15` }}
                    >
                      {p.icon === "key" && (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={p.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
                        </svg>
                      )}
                      {p.icon === "shield" && (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={p.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                      )}
                      {p.icon === "check" && (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={p.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                          <polyline points="9 15 11 17 15 13" />
                        </svg>
                      )}
                      {p.icon === "search" && (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={p.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="11" cy="11" r="8" />
                          <line x1="21" y1="21" x2="16.65" y2="16.65" />
                        </svg>
                      )}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white">{p.pillar}</h3>
                      <span className="text-xs text-gray-500">
                        Covers: {p.sections.join(", ")}
                      </span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {p.automated.map((a) => (
                      <div key={a} className="flex items-center gap-2">
                        <svg className="w-3.5 h-3.5 flex-shrink-0" style={{ color: p.color }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        <span className="text-xs text-gray-400">{a}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Disclaimer */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mt-8 p-4 border border-white/5 rounded-xl"
          >
            <p className="text-xs text-gray-500 leading-relaxed">
              <strong className="text-gray-400">Disclaimer:</strong> This checklist is provided
              as an informational resource to help organizations assess readiness for the EU AI Act.
              It does not constitute legal advice and is not a substitute for professional compliance
              counsel. The EU AI Act requirements may evolve as implementing measures and guidance
              are finalized. AI Identity helps meet these requirements but does not guarantee
              regulatory compliance.
            </p>
          </motion.div>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mt-12 mb-8 text-center no-print"
          >
            <div className="bg-gradient-to-br from-[#F59E0B]/10 to-[#111113]/80 backdrop-blur-xl border border-[#F59E0B]/20 rounded-2xl p-8">
              <h2 className="text-xl md:text-2xl font-bold text-white mb-3">
                Start securing your agents today
              </h2>
              <p className="text-gray-400 text-sm mb-6 max-w-[500px] mx-auto">
                AI Identity automates agent identity, policy enforcement, compliance logging,
                and forensic capabilities — helping your team meet EU AI Act requirements
                with less manual effort.
              </p>
              <div className="flex items-center justify-center gap-4 flex-wrap">
                <a
                  href="https://dashboard.ai-identity.co"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-[#F59E0B] text-[#0A0A0B] font-semibold rounded-xl hover:bg-[#F59E0B]/80 transition-colors"
                >
                  Get Started Free
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </a>
                <a
                  href="https://dashboard.ai-identity.co/demo"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
                >
                  Try the Live Demo
                </a>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
