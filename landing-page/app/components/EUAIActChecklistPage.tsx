import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import Nav from "./landing/Nav";
import Footer from "./landing/Footer";

type Answer = "yes" | "no" | "not-sure";

interface ChecklistItem {
  id: string;
  question: string;
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
      { id: "c1", question: "Do you know which of your AI agents qualify as high-risk under the EU AI Act?", helper: "The Act classifies agents by risk tier — high-risk agents face the strictest requirements." },
      { id: "c2", question: "Have you documented each agent's purpose, scope, and operational boundaries?", helper: "Clear documentation of what each agent does and where it operates is foundational to compliance." },
      { id: "c3", question: "Do you maintain a current inventory or registry of all production agents?", helper: "A living registry ensures no agent is deployed without oversight." },
      { id: "c4", question: "Is there a named human operator responsible for each agent?", helper: "The Act requires a natural or legal person accountable for each high-risk system." },
    ],
  },
  {
    title: "Identity & Traceability",
    article: "Article 13 \u2014 Transparency",
    color: "#F59E0B",
    pillar: "Identity",
    pillarColor: "#F59E0B",
    items: [
      { id: "t1", question: "Does every agent authenticate with its own unique cryptographic identity (not shared API keys)?", helper: "Shared keys make it impossible to attribute actions to a specific agent." },
      { id: "t2", question: "Are agent credentials scoped to only the specific capabilities each agent needs?", helper: "Least-privilege scoping limits blast radius if an agent is compromised." },
      { id: "t3", question: "Is key rotation and lifecycle management automated for your agents?", helper: "Manual rotation leads to stale credentials and gaps in coverage." },
      { id: "t4", question: "Can you trace any agent request back to a specific registered agent identity?", helper: "End-to-end traceability is critical for transparency and accountability." },
    ],
  },
  {
    title: "Risk Management",
    article: "Article 9",
    color: "#EF4444",
    pillar: "Policy",
    pillarColor: "#8B5CF6",
    items: [
      { id: "r1", question: "Have you conducted a risk assessment for each high-risk agent?", helper: "Article 9 mandates a documented risk management process for high-risk AI systems." },
      { id: "r2", question: "Are known limitations and failure modes documented for each agent?", helper: "Users and operators must be informed of what the system cannot do reliably." },
      { id: "r3", question: "Do your systems fail closed (deny on error) rather than fail open?", helper: "Fail-open defaults can allow uncontrolled behavior during outages." },
      { id: "r4", question: "Are residual risks monitored and reviewed on a regular schedule?", helper: "Risk management is continuous — not a one-time checkbox exercise." },
    ],
  },
  {
    title: "Technical Documentation & Logging",
    article: "Article 12 \u2014 Record-Keeping",
    color: "#10B981",
    pillar: "Compliance",
    pillarColor: "#10B981",
    items: [
      { id: "l1", question: "Are all agent decisions logged automatically without manual intervention?", helper: "Automatic logging ensures no decision goes unrecorded." },
      { id: "l2", question: "Are your audit logs tamper-evident (using cryptographic hash chains or equivalent)?", helper: "Tamper-evident logs prove records haven't been altered after the fact." },
      { id: "l3", question: "Is personally identifiable information (PII) automatically sanitized from audit records?", helper: "GDPR and the AI Act both require protecting personal data in logs." },
      { id: "l4", question: "Are logs retained for at least the minimum required period (typically 6\u201312 months)?", helper: "Retention periods vary by jurisdiction and risk classification." },
      { id: "l5", question: "Can you export audit evidence for regulators or auditors on demand?", helper: "Regulators may request evidence at any time — export should be fast and reliable." },
    ],
  },
  {
    title: "Human Oversight",
    article: "Article 14",
    color: "#8B5CF6",
    pillar: "Policy",
    pillarColor: "#8B5CF6",
    items: [
      { id: "h1", question: "Do human-in-the-loop controls exist for high-risk agent decisions?", helper: "Human oversight is non-negotiable for high-risk systems under the Act." },
      { id: "h2", question: "Can you pause or deactivate any agent immediately if needed?", helper: "Kill-switch capability is an explicit requirement for high-risk AI." },
      { id: "h3", question: "Is policy enforcement handled at the infrastructure level so agents cannot bypass rules?", helper: "Agent-side enforcement can be circumvented — infrastructure-level controls cannot." },
      { id: "h4", question: "Are override and intervention procedures documented and accessible?", helper: "Operators must know how to intervene — and the procedures must be tested." },
    ],
  },
  {
    title: "Accuracy, Robustness & Cybersecurity",
    article: "Article 15",
    color: "#06B6D4",
    pillar: "Identity",
    pillarColor: "#F59E0B",
    items: [
      { id: "s1", question: "Does your system validate inputs to prevent injection and manipulation attacks?", helper: "Prompt injection and data manipulation are top threats to agent systems." },
      { id: "s2", question: "Are rate limiting and circuit breakers in place to protect against abuse?", helper: "Without throttling, compromised agents can cause cascading failures." },
      { id: "s3", question: "Are security headers and encryption enforced on all agent communications?", helper: "All agent-to-agent and agent-to-service traffic should be encrypted in transit." },
      { id: "s4", question: "Do you conduct regular security audits of your agent infrastructure?", helper: "Periodic audits catch configuration drift and emerging vulnerabilities." },
    ],
  },
  {
    title: "Post-Market Monitoring & Incident Response",
    article: "Articles 72 & 73",
    color: "#F97316",
    pillar: "Forensics",
    pillarColor: "#EF4444",
    items: [
      { id: "p1", question: "Can your system detect unusual or anomalous agent behavior automatically?", helper: "Anomaly detection is the first line of defense for post-deployment monitoring." },
      { id: "p2", question: "Does your incident response plan include AI agent-specific scenarios?", helper: "Generic IR plans often miss agent-specific failure modes like hallucination loops." },
      { id: "p3", question: "Can you forensically replay and reconstruct any agent incident after the fact?", helper: "Post-incident reconstruction is essential for root cause analysis and evidence." },
      { id: "p4", question: "Can you report serious incidents to authorities with tamper-proof evidence within 72 hours?", helper: "The Act requires timely incident reporting with supporting documentation." },
    ],
  },
];

const totalItems = sections.reduce((acc, s) => acc + s.items.length, 0);

const scoreRanges = [
  { min: 0, max: 9, label: "Critical gaps", desc: "Immediate action needed.", color: "#EF4444" },
  { min: 10, max: 17, label: "Significant gaps", desc: "Prioritize remediation.", color: "#F97316" },
  { min: 18, max: 24, label: "Moderate gaps", desc: "Address before August 2026.", color: "#F59E0B" },
  { min: 25, max: 29, label: "Strong compliance posture", desc: "You're well prepared.", color: "#10B981" },
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

const itemVariant = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

function AnswerButton({
  label,
  value,
  selected,
  onClick,
}: {
  label: string;
  value: Answer;
  selected: boolean;
  onClick: () => void;
}) {
  const colors: Record<Answer, { border: string; bg: string; text: string; selectedText: string }> = {
    yes: { border: "#22C55E", bg: "#22C55E", text: "#22C55E", selectedText: "#052E16" },
    no: { border: "#EF4444", bg: "#EF4444", text: "#EF4444", selectedText: "#450A0A" },
    "not-sure": { border: "#F59E0B", bg: "#F59E0B", text: "#F59E0B", selectedText: "#451A03" },
  };

  const c = colors[value];

  return (
    <button
      onClick={onClick}
      className="px-3 py-1 rounded-md text-xs font-semibold transition-all duration-150 border"
      style={{
        borderColor: selected ? c.border : `${c.border}40`,
        backgroundColor: selected ? c.bg : "transparent",
        color: selected ? c.selectedText : c.text,
      }}
    >
      {label}
    </button>
  );
}

export default function EUAIActChecklistPage() {
  const [answers, setAnswers] = useState<Record<string, Answer>>({});

  const setAnswer = (id: string, value: Answer) => {
    setAnswers((prev) => {
      // Toggle off if clicking same answer
      if (prev[id] === value) {
        const next = { ...prev };
        delete next[id];
        return next;
      }
      return { ...prev, [id]: value };
    });
  };

  const yesCount = useMemo(() => Object.values(answers).filter((a) => a === "yes").length, [answers]);
  const noCount = useMemo(() => Object.values(answers).filter((a) => a === "no").length, [answers]);
  const notSureCount = useMemo(() => Object.values(answers).filter((a) => a === "not-sure").length, [answers]);
  const answeredCount = Object.keys(answers).length;
  const allAnswered = answeredCount === totalItems;

  const currentRange = scoreRanges.find((r) => yesCount >= r.min && yesCount <= r.max) || scoreRanges[0];
  const progressPercent = (yesCount / totalItems) * 100;

  // Section-level gap analysis
  const sectionGaps = useMemo(() => {
    return sections.map((section) => {
      const noItems = section.items.filter((i) => answers[i.id] === "no");
      const notSureItems = section.items.filter((i) => answers[i.id] === "not-sure");
      return {
        title: section.title,
        color: section.color,
        noCount: noItems.length,
        notSureCount: notSureItems.length,
        gapCount: noItems.length + notSureItems.length,
      };
    }).filter((s) => s.gapCount > 0).sort((a, b) => b.gapCount - a.gapCount);
  }, [answers]);

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
              EU AI Act Self-Assessment{" "}
              <span className="text-gray-500">for AI Agents</span>
            </h1>

            <p className="text-lg text-gray-400 max-w-[700px] mx-auto mb-6 leading-relaxed">
              Is your AI agent fleet ready for August 2026? Answer each question below
              to assess your organization's readiness across identity controls, logging,
              human oversight, and incident response.
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
                {yesCount} / {totalItems}
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
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: `${currentRange.color}20`, color: currentRange.color }}
                >
                  {currentRange.label}
                </span>
                <span className="text-xs text-gray-500">{currentRange.desc}</span>
              </div>
              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="text-[#22C55E]">{yesCount} Yes</span>
                <span className="text-gray-600">&middot;</span>
                <span className="text-[#EF4444]">{noCount} No</span>
                <span className="text-gray-600">&middot;</span>
                <span className="text-[#F59E0B]">{notSureCount} Not Sure</span>
              </div>
            </div>
          </motion.div>

          {/* Assessment Sections */}
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="space-y-8"
          >
            {sections.map((section, sectionIdx) => (
              <motion.div
                key={section.title}
                variants={itemVariant}
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

                {/* Questions */}
                <div className="px-6 py-3">
                  {section.items.map((checkItem) => (
                    <div
                      key={checkItem.id}
                      className="checklist-item py-4 border-b border-white/[0.03] last:border-0"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-200 leading-relaxed">
                            {checkItem.question}
                          </p>
                          <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                            {checkItem.helper}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0 pt-0.5">
                          <AnswerButton
                            label="Yes"
                            value="yes"
                            selected={answers[checkItem.id] === "yes"}
                            onClick={() => setAnswer(checkItem.id, "yes")}
                          />
                          <AnswerButton
                            label="No"
                            value="no"
                            selected={answers[checkItem.id] === "no"}
                            onClick={() => setAnswer(checkItem.id, "no")}
                          />
                          <AnswerButton
                            label="Not Sure"
                            value="not-sure"
                            selected={answers[checkItem.id] === "not-sure"}
                            onClick={() => setAnswer(checkItem.id, "not-sure")}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Results Summary — appears when all questions answered */}
          {allAnswered && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="mt-12 bg-[#111113]/80 backdrop-blur-xl border border-white/5 rounded-2xl p-6"
            >
              <h2 className="text-lg font-semibold text-white mb-2">Assessment Results</h2>
              <p className="text-sm text-gray-400 mb-6">
                You answered <span className="text-[#22C55E] font-semibold">{yesCount} Yes</span>,{" "}
                <span className="text-[#EF4444] font-semibold">{noCount} No</span>, and{" "}
                <span className="text-[#F59E0B] font-semibold">{notSureCount} Not Sure</span> out of {totalItems} questions.
              </p>

              {sectionGaps.length > 0 ? (
                <>
                  <h3 className="text-sm font-semibold text-gray-300 mb-3">Sections with gaps</h3>
                  <div className="space-y-2 mb-6">
                    {sectionGaps.map((gap) => (
                      <div
                        key={gap.title}
                        className="flex items-center justify-between p-3 rounded-xl border border-white/5"
                      >
                        <span className="text-sm text-gray-300">{gap.title}</span>
                        <div className="flex items-center gap-3 text-xs font-mono">
                          {gap.noCount > 0 && (
                            <span className="text-[#EF4444]">{gap.noCount} No</span>
                          )}
                          {gap.notSureCount > 0 && (
                            <span className="text-[#F59E0B]">{gap.notSureCount} Not Sure</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-[#22C55E] mb-6">
                  No gaps detected — you answered Yes to all {totalItems} questions.
                </p>
              )}

              <div className="border-t border-white/5 pt-6">
                <a
                  href="https://dashboard.ai-identity.co"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-[#F59E0B] text-[#0A0A0B] font-semibold rounded-xl hover:bg-[#F59E0B]/80 transition-colors"
                >
                  AI Identity can help close these gaps. Get started free
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </a>
              </div>
            </motion.div>
          )}

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
              <strong className="text-gray-400">Disclaimer:</strong> This self-assessment is provided
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
