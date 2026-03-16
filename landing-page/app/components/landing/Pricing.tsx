import { motion } from "framer-motion";

const tiers = [
  {
    name: "Free",
    price: "$0",
    period: "/mo",
    features: ["5 agents", "1,000 requests/day", "Community support", "Basic audit logs"],
    cta: "Get Started Free",
    featured: false,
  },
  {
    name: "Pro",
    price: "$49",
    period: "/mo",
    features: [
      "Unlimited agents",
      "100K requests/day",
      "Priority support",
      "Advanced audit & analytics",
      "Key rotation with grace periods",
    ],
    cta: "Start Pro Trial",
    featured: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    features: [
      "Custom request limits",
      "SLA guarantee",
      "Dedicated support",
      "SSO & SAML",
      "On-premise deployment",
    ],
    cta: "Contact Sales",
    featured: false,
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

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 px-6 bg-[#111113]">
      <div className="max-w-[1200px] mx-auto">
        <motion.h2
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-3xl md:text-5xl font-bold text-white text-center mb-16"
        >
          Simple, transparent pricing
        </motion.h2>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto"
        >
          {tiers.map((tier) => (
            <motion.div
              key={tier.name}
              variants={item}
              className={`relative rounded-2xl p-8 flex flex-col ${
                tier.featured
                  ? "bg-[#111113]/80 backdrop-blur-xl border-2 border-[#F59E0B]/40 shadow-[0_0_40px_rgba(0,255,194,0.08)]"
                  : "bg-[#111113]/80 backdrop-blur-xl border border-white/10"
              }`}
            >
              {tier.featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-[#F59E0B] text-[#0A0A0B] text-xs font-semibold rounded-full">
                  Most Popular
                </span>
              )}

              <h3 className="text-lg font-semibold text-white">{tier.name}</h3>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-bold text-white">
                  {tier.price}
                </span>
                {tier.period && (
                  <span className="text-gray-500 text-sm">{tier.period}</span>
                )}
              </div>

              <ul className="mt-8 flex-1 space-y-3">
                {tier.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-start gap-2 text-sm text-gray-400"
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 16 16"
                      fill="none"
                      className="mt-0.5 shrink-0 text-[#F59E0B]"
                    >
                      <path
                        d="M13.3 4.3L6 11.6 2.7 8.3"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                className={`mt-8 w-full py-3 rounded-lg text-sm font-semibold transition-colors ${
                  tier.featured
                    ? "bg-[#F59E0B] text-[#0A0A0B] hover:bg-[#F59E0B/80]"
                    : "border border-white/20 text-white hover:border-[#F59E0B]/40 hover:bg-white/5"
                }`}
              >
                {tier.cta}
              </button>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
