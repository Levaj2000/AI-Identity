import { motion } from "framer-motion";

export default function FinalCTA() {
  return (
    <section className="py-32 px-6 bg-[#0D0D10]">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="max-w-2xl mx-auto text-center"
      >
        <h2 className="text-3xl md:text-5xl font-bold text-white">
          Give your agents an identity.
        </h2>
        <p className="mt-4 text-lg text-gray-400">
          Start free. Scale when you're ready.
        </p>
        <a
          href="#pricing"
          className="inline-block mt-10 px-10 py-4 bg-[#F59E0B] text-[#0A0A0B] font-semibold rounded-lg hover:bg-[#F59E0B/80] transition-colors text-base"
        >
          Get Started Free &rarr;
        </a>
      </motion.div>
    </section>
  );
}
