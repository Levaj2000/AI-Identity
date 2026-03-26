import { useState } from "react";
import { motion } from "framer-motion";

const frameworks = [
  {
    name: "NIST AI RMF",
    version: "1.0",
    category: "Regulatory",
    checks: 7,
    desc: "NIST AI Risk Management Framework — governance, accountability, and security controls for AI systems.",
    color: "#3B82F6",
  },
  {
    name: "EU AI Act",
    version: "2024",
    category: "Regulatory",
    checks: 8,
    desc: "Helps meet EU AI Act high-risk obligations — cryptographic identities, automated logging, human oversight enforcement, and forensic evidence exports aligned with Articles 9, 12, 13, and 14.",
    color: "#8B5CF6",
  },
  {
    name: "SOC 2",
    version: "2024",
    category: "Industry",
    checks: 7,
    desc: "SOC 2 Trust Service Criteria mapped to AI agent controls — security, availability, and confidentiality.",
    color: "#10B981",
  },
  {
    name: "AI Identity Best Practices",
    version: "1.0",
    category: "Internal",
    checks: 10,
    desc: "Opinionated checks for agent identity management — key hygiene, audit integrity, and governance.",
    color: "#F59E0B",
  },
];

const automatedChecks = [
  { name: "Agent policy governance", icon: "shield" },
  { name: "Least privilege enforcement", icon: "lock" },
  { name: "Audit chain integrity (HMAC)", icon: "link" },
  { name: "Credential encryption at rest", icon: "key" },
  { name: "Key rotation cadence (90-day)", icon: "refresh" },
  { name: "Key type separation", icon: "layers" },
  { name: "Revoked agent key cleanup", icon: "x-circle" },
  { name: "Audit log coverage", icon: "file-text" },
  { name: "Credential prefix identification", icon: "tag" },
  { name: "Agent transparency (descriptions)", icon: "eye" },
  { name: "Capability declaration", icon: "list" },
  { name: "Human oversight enforcement", icon: "eye" },
  { name: "Forensic evidence export readiness", icon: "file-text" },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } },
};

function CheckIcon({ type }: { type: string }) {
  const props = {
    width: 16,
    height: 16,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  switch (type) {
    case "shield":
      return (
        <svg {...props}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      );
    case "lock":
      return (
        <svg {...props}>
          <rect x="3" y="11" width="18" height="11" rx="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      );
    case "link":
      return (
        <svg {...props}>
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
        </svg>
      );
    case "key":
      return (
        <svg {...props}>
          <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
        </svg>
      );
    case "refresh":
      return (
        <svg {...props}>
          <polyline points="23 4 23 10 17 10" />
          <path d="M20.49 15A9 9 0 1 1 21 5.64L23 10" />
        </svg>
      );
    case "layers":
      return (
        <svg {...props}>
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
      );
    case "x-circle":
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      );
    case "file-text":
      return (
        <svg {...props}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      );
    case "tag":
      return (
        <svg {...props}>
          <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
          <line x1="7" y1="7" x2="7.01" y2="7" />
        </svg>
      );
    case "eye":
      return (
        <svg {...props}>
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      );
    case "list":
      return (
        <svg {...props}>
          <line x1="8" y1="6" x2="21" y2="6" />
          <line x1="8" y1="12" x2="21" y2="12" />
          <line x1="8" y1="18" x2="21" y2="18" />
          <line x1="3" y1="6" x2="3.01" y2="6" />
          <line x1="3" y1="12" x2="3.01" y2="12" />
          <line x1="3" y1="18" x2="3.01" y2="18" />
        </svg>
      );
    default:
      return (
        <svg {...props}>
          <polyline points="20 6 9 17 4 12" />
        </svg>
      );
  }
}

export default function ComplianceSection() {
  const [activeFramework, setActiveFramework] = useState(0);

  return (
    <section id="compliance" className="py-24 px-6 bg-[#0A0A0B]">
      <div className="max-w-[1200px] mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[#F59E0B]/10 border border-[#F59E0B]/20 rounded-full mb-6">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#F59E0B"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <polyline points="9 12 11 14 15 10" />
            </svg>
            <span className="text-sm font-medium text-[#F59E0B]">
              Compliance Engine
            </span>
          </div>
          <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
            Compliance built in.{" "}
            <span className="text-gray-500">Not bolted on.</span>
          </h2>
          <p className="max-w-2xl mx-auto text-gray-400 text-lg">
            Run automated assessments against NIST, EU AI Act, SOC 2, and
            internal best practices. Future-proof compliance infrastructure that supports
            high-risk AI obligations out of the box.
          </p>
        </motion.div>

        {/* Stats bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16"
        >
          {[
            { value: "4", label: "Frameworks" },
            { value: "32", label: "Compliance Checks" },
            { value: "13", label: "Auto Evaluators" },
            { value: "< 1s", label: "Assessment Time" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-[#111113]/80 backdrop-blur-xl border border-[#F59E0B]/10 rounded-xl p-5 text-center"
            >
              <div className="text-2xl md:text-3xl font-bold text-[#F59E0B]">
                {stat.value}
              </div>
              <div className="text-xs text-gray-500 mt-1 uppercase tracking-wider">
                {stat.label}
              </div>
            </div>
          ))}
        </motion.div>

        {/* Frameworks grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mb-16"
        >
          <h3 className="text-lg font-semibold text-white mb-6">
            Supported Frameworks
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {frameworks.map((fw, i) => (
              <button
                key={fw.name}
                onClick={() => setActiveFramework(i)}
                className={`text-left bg-[#111113]/80 backdrop-blur-xl border rounded-xl p-5 transition-all ${
                  activeFramework === i
                    ? "border-[#F59E0B]/40 ring-1 ring-[#F59E0B]/20"
                    : "border-white/5 hover:border-white/10"
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{
                      backgroundColor: `${fw.color}15`,
                      color: fw.color,
                    }}
                  >
                    {fw.category}
                  </span>
                  <span className="text-xs text-gray-600">v{fw.version}</span>
                </div>
                <h4 className="text-sm font-semibold text-white mb-2">
                  {fw.name}
                </h4>
                <p className="text-xs text-gray-500 leading-relaxed mb-3">
                  {fw.desc}
                </p>
                <div className="flex items-center gap-1.5">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#F59E0B"
                    strokeWidth="2"
                  >
                    <polyline points="9 11 12 14 22 4" />
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2 2h11" />
                  </svg>
                  <span className="text-xs text-gray-400">
                    {fw.checks} checks
                  </span>
                </div>
              </button>
            ))}
          </div>
        </motion.div>

        {/* Automated checks list */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <h3 className="text-lg font-semibold text-white mb-2">
            13 Automated Evaluators
          </h3>
          <p className="text-sm text-gray-500 mb-6">
            Each check runs automatically against your agents — no manual
            review, no spreadsheets.
          </p>
          <motion.div
            variants={container}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true }}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
          >
            {automatedChecks.map((check) => (
              <motion.div
                key={check.name}
                variants={item}
                className="flex items-center gap-3 bg-[#111113]/60 border border-white/5 rounded-lg px-4 py-3 hover:border-[#F59E0B]/15 transition-colors group"
              >
                <div className="w-7 h-7 flex-shrink-0 flex items-center justify-center rounded-md bg-[#F59E0B]/8 text-[#F59E0B] group-hover:bg-[#F59E0B]/12 transition-colors">
                  <CheckIcon type={check.icon} />
                </div>
                <span className="text-sm text-gray-300">{check.name}</span>
                <svg
                  className="w-4 h-4 ml-auto text-green-500/60"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>

        {/* EU AI Act Callout */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.35 }}
          className="mt-16 bg-gradient-to-br from-[#8B5CF6]/10 to-[#111113]/80 backdrop-blur-xl border border-[#8B5CF6]/20 rounded-2xl p-8 mb-8"
        >
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 flex-shrink-0 flex items-center justify-center rounded-lg bg-[#8B5CF6]/15 text-[#8B5CF6]">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <path d="M2 12h20" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white mb-2">
                Aligned with EU AI Act High-Risk Obligations
              </h3>
              <p className="text-sm text-gray-400 leading-relaxed mb-4">
                AI Identity supports organizations preparing for EU AI Act enforcement.
                Cryptographic agent identities, automated logging, human oversight enforcement,
                and forensic evidence exports help meet the requirements of Articles 9 (Risk Management),
                12 (Record-Keeping), 13 (Transparency), and 14 (Human Oversight).
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  "Cryptographic identity per agent",
                  "Automated, tamper-evident audit logs",
                  "Human oversight enforcement via policies",
                  "One-click forensic evidence export",
                  "Supports EU database registration prep",
                  "Conformity assessment acceleration",
                ].map((item) => (
                  <div key={item} className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-[#8B5CF6] flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <span className="text-xs text-gray-300">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* API Example */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-8 bg-[#111113]/80 backdrop-blur-xl border border-[#F59E0B]/10 rounded-2xl p-8"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-3 h-3 rounded-full bg-red-500/60" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
            <div className="w-3 h-3 rounded-full bg-green-500/60" />
            <span className="ml-2 text-xs text-gray-600 font-mono">
              Run a compliance assessment
            </span>
          </div>
          <pre className="text-sm font-mono overflow-x-auto">
            <code>
              <span className="text-gray-500">
                {"# Run a full compliance assessment against any framework\n"}
              </span>
              <span className="text-green-400">curl</span>
              <span className="text-gray-300">
                {" -X POST https://ai-identity-api.onrender.com"}
              </span>
              <span className="text-[#F59E0B]">
                /api/v1/compliance/reports
              </span>
              {" \\\n"}
              <span className="text-gray-300">{"  -H "}</span>
              <span className="text-blue-400">
                {'"X-API-Key: aid_sk_..."'}
              </span>
              {" \\\n"}
              <span className="text-gray-300">{"  -d "}</span>
              <span className="text-purple-400">
                {'\'{"framework_id": 1}\''}
              </span>
              {"\n\n"}
              <span className="text-gray-500">
                {"# Response: score, pass/fail per check, remediation advice\n"}
              </span>
              <span className="text-gray-300">{"{"}</span>
              {"\n"}
              <span className="text-blue-300">{"  \"score\""}</span>
              <span className="text-gray-300">{": "}</span>
              <span className="text-green-300">{"92.5"}</span>
              <span className="text-gray-300">{","}</span>
              {"\n"}
              <span className="text-blue-300">{"  \"status\""}</span>
              <span className="text-gray-300">{": "}</span>
              <span className="text-green-300">{"\"completed\""}</span>
              <span className="text-gray-300">{","}</span>
              {"\n"}
              <span className="text-blue-300">{"  \"results\""}</span>
              <span className="text-gray-300">{": ["}</span>
              {"\n"}
              <span className="text-gray-300">{"    { "}</span>
              <span className="text-blue-300">{"\"check\""}</span>
              <span className="text-gray-300">{": "}</span>
              <span className="text-green-300">
                {"\"Agent policy governance\""}
              </span>
              <span className="text-gray-300">{", "}</span>
              <span className="text-blue-300">{"\"status\""}</span>
              <span className="text-gray-300">{": "}</span>
              <span className="text-green-300">{"\"pass\""}</span>
              <span className="text-gray-300">{" },"}</span>
              {"\n"}
              <span className="text-gray-300">{"    { "}</span>
              <span className="text-blue-300">{"\"check\""}</span>
              <span className="text-gray-300">{": "}</span>
              <span className="text-green-300">
                {"\"Audit chain integrity\""}
              </span>
              <span className="text-gray-300">{", "}</span>
              <span className="text-blue-300">{"\"status\""}</span>
              <span className="text-gray-300">{": "}</span>
              <span className="text-green-300">{"\"pass\""}</span>
              <span className="text-gray-300">{" },"}</span>
              {"\n"}
              <span className="text-gray-300">{"    ..."}</span>
              {"\n"}
              <span className="text-gray-300">{"  ]"}</span>
              {"\n"}
              <span className="text-gray-300">{"}"}</span>
            </code>
          </pre>
        </motion.div>
      </div>
    </section>
  );
}
