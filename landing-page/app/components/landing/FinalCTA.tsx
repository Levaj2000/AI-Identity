import { motion } from "framer-motion";
import { SerifEmphasis } from "./SerifEmphasis";

export default function FinalCTA() {
  return (
    <section className="py-32 px-6 bg-[#0C1420]">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="max-w-2xl mx-auto text-center"
      >
        <h2 className="text-3xl md:text-5xl font-bold text-white">
          Give your agents an <SerifEmphasis>identity</SerifEmphasis>.
        </h2>
        <p className="mt-4 text-lg text-[#8B9BB4]">
          Start free. Scale when you're ready.
        </p>
        <a
          href="https://dashboard.ai-identity.co"
          className="inline-block mt-10 px-10 py-4 bg-[#F59E0B] text-[#0F1724] font-semibold rounded-lg hover:bg-[#F59E0B]/80 transition-colors text-base"
        >
          Get Started Free &rarr;
        </a>
      </motion.div>
    </section>
  );
}
