import { motion } from "framer-motion";
import { SerifEmphasis } from "./SerifEmphasis";
import { SectionBadge } from "./SectionBadge";

const cards = [
  {
    title: "Per-Request Authentication",
    desc: "Every API call is authenticated independently. No session tokens. No cached trust.",
  },
  {
    title: "Hashed Key Storage",
    desc: "SHA-256 hashed at rest. Keys are never stored in plaintext, never logged, never returned.",
  },
  {
    title: "Future-Proof Compliance Infrastructure",
    desc: "Aligned with SOC 2, NIST AI RMF, and EU AI Act high-risk requirements from day one. Audit trails, access controls, encryption, and automated evidence collection throughout.",
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

export default function SecuritySection() {
  return (
    <section id="security" className="py-24 px-6 bg-[#131E30]">
      <div className="max-w-[1200px] mx-auto">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <SectionBadge label="Security" />
          <h2 className="text-3xl md:text-5xl font-bold text-white">
            Security isn't a feature.{" "}
            <span className="text-[#6B7C96]">It's the <SerifEmphasis>foundation</SerifEmphasis>.</span>
          </h2>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          {cards.map((card) => (
            <motion.div
              key={card.title}
              variants={item}
              className="bg-[#162036]/80 backdrop-blur-xl border border-white/[0.08] hover:border-[#F59E0B]/20 rounded-2xl p-8 transition-colors"
            >
              <h3 className="text-lg font-semibold text-white">{card.title}</h3>
              <p className="mt-3 text-sm text-[#8B9BB4] leading-relaxed">
                {card.desc}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
