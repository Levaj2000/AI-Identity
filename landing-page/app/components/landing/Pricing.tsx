import { motion } from "framer-motion";
import { useState } from "react";

// ── Tier Data ───────────────────────────────────────────────────────

const tiers = [
  {
    name: "Free",
    price: "$0",
    period: "/mo",
    description: "Perfect for prototyping and solo projects.",
    features: [
      "3 agents",
      "5,000 requests/mo",
      "Community support",
      "Basic audit logs (7-day retention)",
      "1 upstream credential",
    ],
    cta: "Get Started Free",
    ctaHref: "https://dashboard.ai-identity.co",
    featured: false,
  },
  {
    name: "Pro",
    price: "$49",
    period: "/mo",
    description: "For teams shipping agents to production.",
    features: [
      "25 agents",
      "100,000 requests/mo",
      "Priority email support",
      "Full audit logs (90-day retention)",
      "10 upstream credentials",
      "Key rotation with grace periods",
      "Gateway policy enforcement",
      "Webhook notifications",
    ],
    cta: "Start Pro Trial",
    ctaHref: "https://dashboard.ai-identity.co",
    featured: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For organizations with compliance requirements.",
    features: [
      "Unlimited agents",
      "Custom request limits",
      "Dedicated support + SLA",
      "Unlimited audit retention",
      "Unlimited credentials",
      "SSO & SAML",
      "SOC 2 compliance report",
      "On-premise deployment option",
    ],
    cta: "Contact Sales",
    ctaHref: "mailto:sales@ai-identity.co",
    featured: false,
  },
];

// ── Feature Comparison Grid ─────────────────────────────────────────

interface ComparisonRow {
  feature: string;
  free: string | boolean;
  pro: string | boolean;
  enterprise: string | boolean;
}

const comparisonRows: ComparisonRow[] = [
  { feature: "Agents", free: "3", pro: "25", enterprise: "Unlimited" },
  {
    feature: "Requests / month",
    free: "5,000",
    pro: "100,000",
    enterprise: "Custom",
  },
  {
    feature: "Upstream credentials",
    free: "1",
    pro: "10",
    enterprise: "Unlimited",
  },
  {
    feature: "Audit log retention",
    free: "7 days",
    pro: "90 days",
    enterprise: "Unlimited",
  },
  {
    feature: "Tamper-proof audit chain",
    free: true,
    pro: true,
    enterprise: true,
  },
  {
    feature: "Key rotation (zero-downtime)",
    free: false,
    pro: true,
    enterprise: true,
  },
  {
    feature: "Gateway policy enforcement",
    free: false,
    pro: true,
    enterprise: true,
  },
  {
    feature: "Webhook notifications",
    free: false,
    pro: true,
    enterprise: true,
  },
  { feature: "Priority support", free: false, pro: true, enterprise: true },
  { feature: "SLA guarantee", free: false, pro: false, enterprise: true },
  { feature: "SSO & SAML", free: false, pro: false, enterprise: true },
  { feature: "SOC 2 report", free: false, pro: false, enterprise: true },
  {
    feature: "On-premise deployment",
    free: false,
    pro: false,
    enterprise: true,
  },
];

// ── FAQ Data ────────────────────────────────────────────────────────

const faqs = [
  {
    q: "What counts as a request?",
    a: "Every call through the AI Identity gateway counts as one request \u2014 whether it's a policy check, credential retrieval, or proxied API call. Internal dashboard actions (listing agents, viewing audit logs) don't count.",
  },
  {
    q: "Can I change plans at any time?",
    a: "Yes. Upgrade instantly, downgrade at the end of your billing cycle. Your agents and audit logs are preserved across plan changes.",
  },
  {
    q: "What happens if I exceed my request limit?",
    a: "We'll send you a heads-up at 80% usage. If you exceed the limit, requests are rate-limited (not dropped) until the next billing cycle. You can upgrade anytime to increase your limit.",
  },
  {
    q: "Is there a free trial for Pro?",
    a: "Yes \u2014 14-day free trial with full Pro features. No credit card required to start.",
  },
  {
    q: "Do you offer discounts for startups or open-source projects?",
    a: "Yes. Startups with less than $1M in funding get 50% off Pro for the first year. Qualifying open-source projects get Pro free. Email us at sales@ai-identity.co.",
  },
  {
    q: "How does Enterprise pricing work?",
    a: "Enterprise pricing is based on your agent count, request volume, and deployment requirements. We'll scope it on a call \u2014 most Enterprise deals start at $500/mo.",
  },
];

// ── Animations ──────────────────────────────────────────────────────

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const cardVariant = {
  hidden: { opacity: 0, y: 30 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" },
  },
};

// ── Icons ───────────────────────────────────────────────────────────

function CheckIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className="shrink-0 text-[#F59E0B]"
    >
      <path
        d="M13.3 4.3L6 11.6 2.7 8.3"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function XIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className="shrink-0 text-gray-600"
    >
      <path
        d="M4 4l8 8M12 4l-8 8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CellValue({ value }: { value: string | boolean }) {
  if (typeof value === "boolean") {
    return value ? <CheckIcon /> : <XIcon />;
  }
  return <span className="text-sm text-gray-300">{value}</span>;
}

// ── Component ───────────────────────────────────────────────────────

export default function Pricing() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <section id="pricing" className="py-24 px-6 bg-[#111113]">
      <div className="max-w-[1200px] mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-5xl font-bold text-white">
            Simple, transparent pricing
          </h2>
          <p className="mt-4 text-lg text-gray-400 max-w-2xl mx-auto">
            Start free. Scale as your agents grow. Every plan includes the
            tamper-proof audit chain.
          </p>
          <p className="mt-2 text-sm text-gray-500">
            Prices are draft &mdash; we&apos;re validating with design partners.
          </p>
        </motion.div>

        {/* ── Pricing Cards ────────────────────────────────────────── */}
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
              variants={cardVariant}
              className={`relative rounded-2xl p-8 flex flex-col ${
                tier.featured
                  ? "bg-[#111113]/80 backdrop-blur-xl border-2 border-[#F59E0B]/40 shadow-[0_0_40px_rgba(245,158,11,0.08)]"
                  : "bg-[#111113]/80 backdrop-blur-xl border border-white/10"
              }`}
            >
              {tier.featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-[#F59E0B] text-[#0A0A0B] text-xs font-semibold rounded-full">
                  Most Popular
                </span>
              )}

              <h3 className="text-lg font-semibold text-white">{tier.name}</h3>
              <p className="mt-1 text-sm text-gray-500">{tier.description}</p>
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
                    <span className="mt-0.5">
                      <CheckIcon />
                    </span>
                    {f}
                  </li>
                ))}
              </ul>

              <a
                href={tier.ctaHref}
                className={`mt-8 w-full py-3 rounded-lg text-sm font-semibold transition-colors text-center block ${
                  tier.featured
                    ? "bg-[#F59E0B] text-[#0A0A0B] hover:bg-[#F59E0B]/80"
                    : "border border-white/20 text-white hover:border-[#F59E0B]/40 hover:bg-white/5"
                }`}
              >
                {tier.cta}
              </a>
            </motion.div>
          ))}
        </motion.div>

        {/* ── Feature Comparison Grid ──────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-24"
        >
          <h3 className="text-2xl md:text-3xl font-bold text-white text-center mb-10">
            Compare plans
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full max-w-4xl mx-auto">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="py-4 px-4 text-left text-sm font-medium text-gray-500 w-1/3">
                    Feature
                  </th>
                  <th className="py-4 px-4 text-center text-sm font-medium text-gray-400">
                    Free
                  </th>
                  <th className="py-4 px-4 text-center text-sm font-semibold text-[#F59E0B]">
                    Pro
                  </th>
                  <th className="py-4 px-4 text-center text-sm font-medium text-gray-400">
                    Enterprise
                  </th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row, i) => (
                  <tr
                    key={row.feature}
                    className={`border-b border-white/5 ${i % 2 === 0 ? "bg-white/[0.02]" : ""}`}
                  >
                    <td className="py-3 px-4 text-sm text-gray-300">
                      {row.feature}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="inline-flex justify-center">
                        <CellValue value={row.free} />
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="inline-flex justify-center">
                        <CellValue value={row.pro} />
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="inline-flex justify-center">
                        <CellValue value={row.enterprise} />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* ── FAQ Section ──────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-24 max-w-3xl mx-auto"
        >
          <h3 className="text-2xl md:text-3xl font-bold text-white text-center mb-10">
            Frequently asked questions
          </h3>

          <div className="space-y-2">
            {faqs.map((faq, i) => (
              <div
                key={i}
                className="rounded-xl border border-white/10 overflow-hidden transition-colors hover:border-white/20"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between px-6 py-4 text-left"
                >
                  <span className="text-sm font-medium text-white pr-4">
                    {faq.q}
                  </span>
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="none"
                    className={`shrink-0 text-gray-500 transition-transform duration-200 ${
                      openFaq === i ? "rotate-180" : ""
                    }`}
                  >
                    <path
                      d="M5 7.5l5 5 5-5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                {openFaq === i && (
                  <div className="px-6 pb-4">
                    <p className="text-sm text-gray-400 leading-relaxed">
                      {faq.a}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
