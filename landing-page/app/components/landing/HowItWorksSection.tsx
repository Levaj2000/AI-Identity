import { motion } from "framer-motion";

const steps = [
  {
    num: "01",
    title: "Register",
    desc: "Register your agent and get a unique API key in one call. The key is hashed, shown once, and tied to your agent's lifecycle.",
  },
  {
    num: "02",
    title: "Authenticate",
    desc: "The gateway verifies every agent's API key against its hashed record before any request proceeds. No shortcuts. No exceptions.",
  },
  {
    num: "03",
    title: "Audit",
    desc: "Every action is logged to an append-only audit trail. See who did what, when, and with which key.",
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

export default function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-24 px-6 bg-[#111113]">
      <div className="max-w-[1200px] mx-auto">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center text-center mb-16"
        >
          <span className="inline-block px-4 py-1.5 border border-[#F59E0B]/30 rounded-full text-[#F59E0B] text-xs font-medium tracking-widest uppercase mb-6">
            How It Works
          </span>
          <h2 className="text-3xl md:text-5xl font-bold text-white">
            Three steps to secure your agents
          </h2>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          {steps.map((step) => (
            <motion.div
              key={step.num}
              variants={item}
              className="bg-[#111113]/80 backdrop-blur-xl border border-[#F59E0B]/10 rounded-2xl p-8 hover:border-[#F59E0B]/25 transition-colors"
            >
              <span className="text-5xl font-bold text-[#F59E0B]/30">
                {step.num}
              </span>
              <h3 className="mt-4 text-xl font-semibold text-white">
                {step.title}
              </h3>
              <p className="mt-3 text-sm text-gray-400 leading-relaxed">
                {step.desc}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
