import { motion } from "framer-motion";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-[72px] overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-[#F59E0B]/5 rounded-full blur-[120px] pointer-events-none" />

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
          <span className="text-[#F59E0B]">an identity.</span>
        </h1>

        {/* Subtitle */}
        <p className="mt-6 text-lg md:text-xl text-gray-400 max-w-2xl leading-relaxed">
          Per-agent API keys, scoped permissions, and tamper-proof audit trails.
          Deploy in 15 minutes, not 15 weeks.
        </p>

        {/* Buttons */}
        <div className="mt-10 flex flex-col sm:flex-row gap-4">
          <a
            href="https://dashboard.ai-identity.co"
            className="px-8 py-3.5 bg-[#F59E0B] text-[#0A0A0B] font-semibold rounded-lg hover:bg-[#F59E0B]/80 transition-colors text-sm"
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
