import { motion } from "framer-motion";

export default function DashboardPreview() {
  return (
    <section className="py-24 px-6 bg-[#0A0A0B]">
      <div className="max-w-[1200px] mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-5xl font-bold text-white">
            See everything. Control everything.
          </h2>
          <p className="mt-4 text-lg text-gray-400 max-w-2xl mx-auto">
            Monitor agent activity, manage keys, and enforce policies from a
            single dashboard.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="relative"
        >
          {/* Glow */}
          <div className="absolute -inset-4 bg-[#F59E0B]/5 rounded-3xl blur-[40px] pointer-events-none" />

          {/* Browser mockup */}
          <div className="relative border border-[#F59E0B]/10 rounded-2xl overflow-hidden bg-[#111113]">
            {/* Title bar */}
            <div className="flex items-center gap-2 px-5 py-3 bg-[#0A0A0B] border-b border-white/5">
              <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
              <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
              <div className="w-3 h-3 rounded-full bg-[#28c840]" />
              <div className="flex-1 text-center">
                <span className="text-xs text-gray-500">
                  dashboard.ai-identity.co
                </span>
              </div>
            </div>
            {/* Content placeholder */}
            <div className="flex items-center justify-center h-[400px] md:h-[500px] bg-gradient-to-br from-[#111113] to-[#0A0A0B]">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-[#F59E0B]/10 flex items-center justify-center">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="3" width="7" height="7" />
                    <rect x="14" y="3" width="7" height="7" />
                    <rect x="14" y="14" width="7" height="7" />
                    <rect x="3" y="14" width="7" height="7" />
                  </svg>
                </div>
                <p className="text-gray-500 text-sm">
                  Dashboard Preview — Screenshot Coming Soon
                </p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
