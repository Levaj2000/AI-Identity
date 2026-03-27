import { motion } from "framer-motion";
import { SerifEmphasis } from "./SerifEmphasis";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-[72px] overflow-hidden">
      {/* Atmospheric mist */}
      <motion.div
        className="absolute top-1/4 left-1/4 w-[600px] h-[400px] rounded-full bg-[#1E3A5F]/30 blur-[150px]"
        animate={{ opacity: [0.03, 0.08, 0.03] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-1/3 right-1/4 w-[500px] h-[350px] rounded-full bg-[#2A4A7F]/20 blur-[130px]"
        animate={{ opacity: [0.05, 0.1, 0.05] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut", delay: 2 }}
      />
      <motion.div
        className="absolute bottom-1/4 left-1/3 w-[400px] h-[300px] rounded-full bg-[#F59E0B]/5 blur-[120px]"
        animate={{ opacity: [0.02, 0.05, 0.02] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut", delay: 4 }}
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="relative z-10 flex flex-col items-center text-center max-w-4xl mx-auto"
      >
        {/* Badge */}
        <div className="mb-8 px-4 py-1.5 border border-[#F59E0B]/30 rounded-full text-[#F59E0B] text-xs font-medium tracking-widest uppercase">
          &#10022; Identity for AI Agents
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold leading-[1.05] tracking-tight">
          <span className="text-white">Every agent gets</span>
          <br />
          <span className="text-[#F59E0B]">an <SerifEmphasis>identity</SerifEmphasis>.</span>
        </h1>

        {/* Subtitle */}
        <p className="mt-6 text-lg md:text-xl text-[#8B9BB4] max-w-2xl leading-relaxed">
          Per-agent API keys, scoped permissions, and tamper-proof audit trails.
          Deploy in 15 minutes, not 15 weeks.
        </p>

        {/* Buttons */}
        <div className="mt-10 flex flex-col sm:flex-row gap-4">
          <a
            href="https://dashboard.ai-identity.co"
            className="px-8 py-3.5 bg-[#F59E0B] text-[#0F1724] font-semibold rounded-lg hover:bg-[#F59E0B]/80 transition-colors text-sm"
          >
            Get Started Free &rarr;
          </a>
          <a
            href="/docs"
            className="px-8 py-3.5 border border-white/20 text-white font-medium rounded-lg hover:border-white/40 hover:bg-white/5 transition-all text-sm"
          >
            View API Docs
          </a>
        </div>
      </motion.div>

      {/* Hero device image */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
        className="relative z-10 mt-16 w-full max-w-4xl mx-auto"
      >
        {/* Glow behind image */}
        <div className="absolute inset-0 bg-[#F59E0B]/8 rounded-3xl blur-[60px] -z-10" />
        <img
          src="/images/hero-device.jpg"
          alt="AI Identity dashboard"
          className="w-full rounded-xl shadow-2xl shadow-black/50"
        />
      </motion.div>
    </section>
  );
}
