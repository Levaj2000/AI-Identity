import { motion } from "framer-motion";
import { SerifEmphasis } from "./SerifEmphasis";

const pillars = [
  {
    label: "Identity",
    question: "Who is this agent?",
    desc: "Unique API keys, scoped permissions, lifecycle management.",
    active: false,
  },
  {
    label: "Policy",
    question: "What can it do?",
    desc: "Fail-closed gateway, per-request policy evaluation.",
    active: false,
  },
  {
    label: "Compliance",
    question: "Can we prove it?",
    desc: "Automated evaluators, SOC 2 / NIST / EU AI Act mapping.",
    active: false,
  },
  {
    label: "Forensics",
    question: "What happened?",
    desc: "Incident replay, chain verification, forensic export.",
    active: true,
  },
];

const capabilities = [
  {
    title: "Incident Replay",
    desc: "Reconstruct every action an agent took — requests, policy decisions, and outcomes — in chronological order with full context.",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
  },
  {
    title: "Chain Verification",
    desc: "One API call confirms the integrity of the entire audit chain. HMAC-SHA256 hash linking makes any tampering immediately detectable.",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    title: "Anomaly Detection",
    desc: "Flag agents that deviate from established behavior patterns — new endpoints, unusual request volumes, or access outside normal hours.",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
  },
  {
    title: "Forensic Export",
    desc: "Auditor-ready reports in JSON and PDF. Evidence that supports EU AI Act conformity assessments, SOC 2 audits, and regulatory inquiries — for compliance teams, legal counsel, and external auditors.",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </svg>
    ),
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export default function ForensicsSection() {
  return (
    <section id="forensics" className="py-24 px-6 bg-[#0F1724]">
      <div className="max-w-[1200px] mx-auto">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center text-center mb-16"
        >
          <span className="inline-block px-4 py-1.5 border border-[#F59E0B]/30 rounded-full text-[#F59E0B] text-xs font-medium tracking-widest uppercase mb-6">
            AI Forensics
          </span>
          <h2 className="text-3xl md:text-5xl font-bold text-white">
            When something goes wrong,{" "}
            <span className="text-[#6B7C96]"><SerifEmphasis>prove</SerifEmphasis> what happened.</span>
          </h2>
          <p className="mt-4 text-[#8B9BB4] max-w-2xl text-lg">
            Tamper-evident audit chains, incident replay, and forensic export.
            Not monitoring — proof.
          </p>
        </motion.div>

        {/* Four pillars */}
        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16"
        >
          {pillars.map((pillar) => (
            <motion.div
              key={pillar.label}
              variants={item}
              className={`rounded-2xl p-6 border transition-colors ${
                pillar.active
                  ? "bg-[#F59E0B]/10 border-[#F59E0B]/30"
                  : "bg-[#162036]/80 border-white/5 hover:border-white/10"
              }`}
            >
              <span
                className={`text-xs font-semibold tracking-widest uppercase ${
                  pillar.active ? "text-[#F59E0B]" : "text-[#6B7C96]"
                }`}
              >
                {pillar.label}
              </span>
              <p className="mt-2 text-white font-semibold text-sm">
                {pillar.question}
              </p>
              <p className="mt-1 text-xs text-[#8B9BB4] leading-relaxed">
                {pillar.desc}
              </p>
            </motion.div>
          ))}
        </motion.div>

        {/* Capabilities grid */}
        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 gap-6"
        >
          {capabilities.map((cap) => (
            <motion.div
              key={cap.title}
              variants={item}
              className="bg-[#162036]/80 backdrop-blur-xl border border-white/[0.08] hover:border-[#F59E0B]/20 rounded-2xl p-8 transition-colors group"
            >
              <div className="w-10 h-10 flex items-center justify-center rounded-lg bg-[#F59E0B]/10 text-[#F59E0B] mb-5 group-hover:bg-[#F59E0B]/15 transition-colors">
                {cap.icon}
              </div>
              <h3 className="text-lg font-semibold text-white">{cap.title}</h3>
              <p className="mt-2 text-sm text-[#8B9BB4] leading-relaxed">
                {cap.desc}
              </p>
            </motion.div>
          ))}
        </motion.div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-12 text-center"
        >
          <a
            href="/blog/introducing-ai-forensics"
            className="inline-flex items-center gap-2 text-[#F59E0B] text-sm font-medium hover:underline"
          >
            Read: Introducing AI Forensics
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </a>
        </motion.div>
      </div>
    </section>
  );
}
