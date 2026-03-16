import { motion } from "framer-motion";

export default function SocialProof() {
  return (
    <section className="py-20 px-6 border-t border-white/5">
      <motion.p
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="text-center text-sm text-gray-500 tracking-wide uppercase"
      >
        Trusted by teams building the next generation of AI agents
      </motion.p>
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="mt-10 flex flex-wrap items-center justify-center gap-x-12 gap-y-6"
      >
        {["Acme AI", "NovaTech", "AgentForge", "Cortex Labs", "Synth.io"].map(
          (name) => (
            <span
              key={name}
              className="text-gray-600 text-lg font-semibold tracking-wide"
            >
              {name}
            </span>
          )
        )}
      </motion.div>
    </section>
  );
}
