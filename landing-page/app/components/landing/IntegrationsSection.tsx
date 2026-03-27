import { motion } from "framer-motion";
import { SerifEmphasis } from "./SerifEmphasis";
import { SectionBadge } from "./SectionBadge";

const integrations = [
  {
    name: "Python",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2C6.48 2 2 4.02 2 6.5V12c0 2.48 4.48 4.5 10 4.5h0" />
        <path d="M22 12v5.5c0 2.48-4.48 4.5-10 4.5h0" />
        <path d="M2 6.5C2 8.98 6.48 11 12 11s10-2.02 10-4.5S17.52 2 12 2" />
        <circle cx="7" cy="5" r="1" fill="currentColor" />
        <circle cx="17" cy="19" r="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    name: "TypeScript",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M8 17V11h4" />
        <path d="M6 11h6" />
        <path d="M15 11c1.1 0 2 .45 2 1.5s-.9 1.5-2 1.5 2 .45 2 1.5-.9 1.5-2 1.5" />
      </svg>
    ),
  },
  {
    name: "LangChain",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13.828 10.172a4 4 0 0 0-5.656 0l-4 4a4 4 0 1 0 5.656 5.656l1.102-1.101" />
        <path d="M10.172 13.828a4 4 0 0 0 5.656 0l4-4a4 4 0 1 0-5.656-5.656l-1.102 1.101" />
      </svg>
    ),
  },
  {
    name: "CrewAI",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    name: "AutoGen",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
  },
  {
    name: "cURL",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 17 10 11 4 5" />
        <line x1="12" y1="19" x2="20" y2="19" />
      </svg>
    ),
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, scale: 0.95 },
  show: { opacity: 1, scale: 1, transition: { duration: 0.4 } },
};

const codeSnippet = `curl -X POST https://api.ai-identity.co/v1/agents \\
  -H "Authorization: Bearer aid_sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{"name": "my-agent", "capabilities": ["read", "write"]}'`;

export default function IntegrationsSection() {
  return (
    <section id="integrations" className="py-24 px-6 bg-[#0F1724]">
      <div className="max-w-[1200px] mx-auto">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <SectionBadge label="Integrations" />
          <h2 className="text-3xl md:text-5xl font-bold text-white">
            Works with your <SerifEmphasis>stack</SerifEmphasis>
          </h2>
          <p className="mt-4 text-lg text-[#8B9BB4] max-w-xl mx-auto">
            Standard REST API. No proprietary SDKs. Integrate in minutes.
          </p>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4 mb-16"
        >
          {integrations.map((i) => (
            <motion.div
              key={i.name}
              variants={item}
              className="flex flex-col items-center gap-3 py-6 px-4 bg-[#162036]/80 backdrop-blur-xl border border-white/5 rounded-xl hover:border-[#F59E0B]/20 transition-colors"
            >
              <div className="text-[#F59E0B]">{i.icon}</div>
              <span className="text-sm text-gray-300 font-medium">
                {i.name}
              </span>
            </motion.div>
          ))}
        </motion.div>

        {/* Code snippet */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="relative max-w-3xl mx-auto"
        >
          <div className="absolute -inset-1 bg-[#F59E0B]/5 rounded-2xl blur-[20px] pointer-events-none" />
          <div className="relative bg-[#131E30] border border-white/[0.08] hover:border-[#F59E0B]/20 rounded-xl overflow-hidden transition-colors">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5">
              <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
              <span className="ml-2 text-xs text-[#6B7C96]">terminal</span>
            </div>
            <pre className="p-6 text-sm text-gray-300 overflow-x-auto">
              <code>{codeSnippet}</code>
            </pre>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
