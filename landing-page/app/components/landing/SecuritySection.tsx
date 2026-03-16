import { motion } from "framer-motion";

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
    title: "Designed for SOC 2",
    desc: "Built with SOC 2 compliance principles from day one. Audit trails, access controls, and encryption throughout.",
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
    <section id="security" className="py-24 px-6 bg-[#111113]">
      <div className="max-w-[1200px] mx-auto">
        <motion.h2
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-3xl md:text-5xl font-bold text-white text-center mb-16"
        >
          Security isn't a feature.{" "}
          <span className="text-gray-500">It's the architecture.</span>
        </motion.h2>

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
              className="bg-[#111113]/80 backdrop-blur-xl border border-[#F59E0B]/10 rounded-2xl p-8 hover:border-[#F59E0B]/25 transition-colors"
            >
              <h3 className="text-lg font-semibold text-white">{card.title}</h3>
              <p className="mt-3 text-sm text-gray-400 leading-relaxed">
                {card.desc}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
