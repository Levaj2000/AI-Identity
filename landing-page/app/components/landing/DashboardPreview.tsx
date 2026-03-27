import { motion } from "framer-motion";
import { SerifEmphasis } from "./SerifEmphasis";
import { SectionBadge } from "./SectionBadge";

export default function DashboardPreview() {
  return (
    <section className="py-24 px-6 bg-[#0F1724]">
      <div className="max-w-[1200px] mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <SectionBadge label="Dashboard" />
          <h2 className="text-3xl md:text-5xl font-bold text-white">
            See everything. <SerifEmphasis>Control</SerifEmphasis> everything.
          </h2>
          <p className="mt-4 text-lg text-[#8B9BB4] max-w-2xl mx-auto">
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
          <div className="relative border border-white/[0.08] hover:border-[#F59E0B]/20 rounded-2xl overflow-hidden bg-[#131E30] transition-colors">
            {/* Title bar */}
            <div className="flex items-center gap-2 px-5 py-3 bg-[#0F1724] border-b border-white/5">
              <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
              <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
              <div className="w-3 h-3 rounded-full bg-[#28c840]" />
              <div className="flex-1 text-center">
                <span className="text-xs text-[#6B7C96]">
                  dashboard.ai-identity.co
                </span>
              </div>
            </div>
            {/* Dashboard screenshot */}
            <img
              src="/images/dashboard-preview.jpg"
              alt="AI Identity Dashboard — agent management, request volume, and system health"
              className="w-full"
            />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
