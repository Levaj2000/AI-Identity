import { motion } from "framer-motion";
import { useState } from "react";
import SEO, { softwareApplicationSchema } from "../components/SEO";

// ── Tier Data ───────────────────────────────────────────────────────

const tiers = [
  {
    name: "Free",
    monthlyPrice: 0,
    annualPrice: 0,
    description: "Perfect for prototyping and solo projects.",
    features: [
      "5 agents",
      "2,000 requests/mo",
      "1 team member",
      "Community support",
      "Audit logs (30-day retention)",
      "1 upstream credential",
    ],
    cta: "Get Started Free",
    ctaHref: "https://dashboard.ai-identity.co",
    featured: false,
  },
  {
    name: "Pro",
    monthlyPrice: 79,
    annualPrice: 67,
    description: "For teams shipping agents to production.",
    features: [
      "50 agents",
      "75,000 requests/mo",
      "Up to 5 team members",
      "Email support",
      "Full audit logs (90-day retention)",
      "10 upstream credentials",
      "Key rotation with grace periods",
      "Gateway policy enforcement",
      "Basic SSO",
    ],
    cta: "Start Pro Trial",
    ctaHref: "https://dashboard.ai-identity.co",
    featured: true,
  },
  {
    name: "Business",
    monthlyPrice: 299,
    annualPrice: 254,
    description: "For scaling teams with advanced requirements.",
    features: [
      "200 agents",
      "500,000 requests/mo",
      "Up to 25 team members",
      "Priority support",
      "1-year audit retention",
      "50 upstream credentials",
      "Custom policies",
      "SAML / SCIM",
      "Team roles & permissions",
      "Agent-level role assignments",
    ],
    cta: "Start Business Trial",
    ctaHref: "https://dashboard.ai-identity.co",
    featured: false,
  },
  {
    name: "Enterprise",
    monthlyPrice: -1,
    annualPrice: -1,
    description: "For organizations with compliance requirements.",
    features: [
      "Unlimited agents",
      "Unlimited requests",
      "Unlimited team members",
      "Dedicated support + SLA",
      "Unlimited audit retention",
      "Unlimited credentials",
      "Full SSO & SAML",
      "Compliance evidence export",
      "Team roles & agent assignments",
      "Human-in-the-loop review",
      "On-premise / VPC deployment",
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
  business: string | boolean;
  enterprise: string | boolean;
}

const comparisonRows: ComparisonRow[] = [
  { feature: "Agents", free: "5", pro: "50", business: "200", enterprise: "Unlimited" },
  { feature: "Requests / month", free: "2,000", pro: "75,000", business: "500,000", enterprise: "Unlimited" },
  { feature: "Upstream credentials", free: "1", pro: "10", business: "50", enterprise: "Unlimited" },
  { feature: "Audit log retention", free: "30 days", pro: "90 days", business: "1 year", enterprise: "Unlimited" },
  { feature: "Tamper-proof audit chain", free: true, pro: true, business: true, enterprise: true },
  { feature: "Key rotation (zero-downtime)", free: false, pro: true, business: true, enterprise: true },
  { feature: "Gateway policy enforcement", free: false, pro: true, business: true, enterprise: true },
  { feature: "Custom policies", free: false, pro: false, business: true, enterprise: true },
  { feature: "Team members", free: "1", pro: "5", business: "25", enterprise: "Unlimited" },
  { feature: "Team roles & permissions", free: false, pro: false, business: true, enterprise: true },
  { feature: "Agent-level assignments", free: false, pro: false, business: true, enterprise: true },
  { feature: "SSO", free: false, pro: "Basic", business: "SAML / SCIM", enterprise: "Full" },
  { feature: "Priority support", free: false, pro: false, business: true, enterprise: true },
  { feature: "SLA guarantee", free: false, pro: false, business: false, enterprise: true },
  { feature: "Compliance evidence export", free: false, pro: false, business: false, enterprise: true },
  { feature: "Human-in-the-loop review", free: false, pro: false, business: false, enterprise: true },
  { feature: "On-premise / VPC", free: false, pro: false, business: false, enterprise: true },
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
    q: "Is there a free trial?",
    a: "Yes \u2014 14-day free trial on Pro and Business with full features. No credit card required to start.",
  },
  {
    q: "Do you offer discounts for startups or open-source projects?",
    a: "Yes. Our Founder Rate gives the first 5\u201310 customers 50% off for 6 months in exchange for a case study and feedback. Qualifying open-source projects get Pro free. Email us at sales@ai-identity.co.",
  },
  {
    q: "How does Enterprise pricing work?",
    a: "Enterprise pricing is based on your agent count, request volume, and deployment requirements. We'll scope it on a call \u2014 most Enterprise deals start around $1,200/mo.",
  },
];

// ── Animations ──────────────────────────────────────────────────────

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
} as const;

const cardVariant = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

// ── Icons ───────────────────────────────────────────────────────────

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 text-[rgb(166,218,255)]">
      <path d="M13.3 4.3L6 11.6 2.7 8.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 text-gray-600">
      <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function CellValue({ value }: { value: string | boolean }) {
  if (typeof value === "boolean") return value ? <CheckIcon /> : <XIcon />;
  return <span className="text-sm text-gray-300">{value}</span>;
}

// ── Usage Estimator ─────────────────────────────────────────────────

const tierThresholds = [
  { name: "Free", maxAgents: 5, maxRequests: 2_000, price: "$0/mo" },
  { name: "Pro", maxAgents: 50, maxRequests: 75_000, price: "$79/mo" },
  { name: "Business", maxAgents: 200, maxRequests: 500_000, price: "$299/mo" },
  { name: "Enterprise", maxAgents: Infinity, maxRequests: Infinity, price: "Custom" },
];

function UsageEstimator() {
  const [agents, setAgents] = useState(10);
  const [reqPerAgent, setReqPerAgent] = useState(3000);

  const totalRequests = agents * reqPerAgent;
  const recommended = tierThresholds.find(
    (t) => agents <= t.maxAgents && totalRequests <= t.maxRequests,
  ) ?? tierThresholds[tierThresholds.length - 1];

  const tierColorMap: Record<string, string> = {
    Free: "text-gray-400",
    Pro: "text-[rgb(166,218,255)]",
    Business: "text-blue-400",
    Enterprise: "text-purple-400",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay: 0.15 }}
      className="mt-16 max-w-2xl mx-auto"
    >
      <div className="rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(16,19,28)]/80 backdrop-blur-xl p-8">
        <div className="mb-6">
          <div className="flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
            <h3 className="text-lg font-semibold text-white">How much will it cost?</h3>
          </div>
          <p className="mt-1.5 text-sm text-[rgba(213,219,230,0.5)] ml-[26px]">
            See your projected usage in real time.
          </p>
        </div>

        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-[rgba(213,219,230,0.6)]">Active agents</label>
              <span className="text-sm font-mono font-semibold text-white">{agents}</span>
            </div>
            <input
              type="range" min={1} max={250} value={agents}
              onChange={(e) => setAgents(Number(e.target.value))}
              className="w-full h-1.5 rounded-full bg-[rgba(216,231,242,0.07)] appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[rgb(166,218,255)]"
            />
            <div className="flex justify-between mt-1 text-[10px] text-[rgba(213,219,230,0.3)]">
              <span>1</span><span>50</span><span>100</span><span>200</span><span>250</span>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-[rgba(213,219,230,0.6)]">Requests per agent / month</label>
              <span className="text-sm font-mono font-semibold text-white">{reqPerAgent.toLocaleString()}</span>
            </div>
            <input
              type="range" min={100} max={10000} step={100} value={reqPerAgent}
              onChange={(e) => setReqPerAgent(Number(e.target.value))}
              className="w-full h-1.5 rounded-full bg-[rgba(216,231,242,0.07)] appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[rgb(166,218,255)]"
            />
            <div className="flex justify-between mt-1 text-[10px] text-[rgba(213,219,230,0.3)]">
              <span>100</span><span>2.5k</span><span>5k</span><span>7.5k</span><span>10k</span>
            </div>
          </div>

          <div className="rounded-xl bg-white/[0.03] border border-[rgba(216,231,242,0.07)] p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[rgba(213,219,230,0.4)] uppercase tracking-wider">Estimated monthly volume</p>
                <p className="mt-1 text-xl font-bold text-white">
                  {totalRequests.toLocaleString()}{" "}
                  <span className="text-sm font-normal text-[rgba(213,219,230,0.5)]">requests/mo</span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-[rgba(213,219,230,0.4)] uppercase tracking-wider">Recommended plan</p>
                <p className={`mt-1 text-xl font-bold ${tierColorMap[recommended.name] ?? "text-white"}`}>
                  {recommended.name}
                </p>
                <p className="text-sm text-[rgba(213,219,230,0.5)]">{recommended.price}</p>
              </div>
            </div>
          </div>

          <p className="text-xs text-[rgba(213,219,230,0.35)] leading-relaxed">
            Most teams with 10-20 active agents stay under 75k requests/mo.
            Heavy QA or forensics runs? Overages billed at ~$1 per 1k extra requests.{" "}
            <a href="https://dashboard.ai-identity.co" className="text-[rgb(166,218,255)] hover:underline">
              Try the dashboard
            </a>{" "}
            to simulate your exact volume.
          </p>
        </div>
      </div>
    </motion.div>
  );
}

// ── Page Component ──────────────────────────────────────────────────

export default function Pricing() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [annual, setAnnual] = useState(false);

  return (
    <div className="py-24 px-6">
      <SEO
        title="Pricing — AI Agent Identity & Compliance"
        description="Simple, transparent pricing for AI agent identity infrastructure. Free tier for 5 agents. Pro from $79/mo. Business from $299/mo. Enterprise custom."
        path="/pricing"
        jsonLd={softwareApplicationSchema}
      />
      <div className="max-w-[1200px] mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-[44px] font-medium text-white leading-[1.2]">
            Simple,{" "}
            <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
              Transparent
            </span>{" "}
            Pricing
          </h2>
          <p className="mt-4 text-lg text-[rgba(213,219,230,0.6)] max-w-2xl mx-auto">
            Start free. Scale securely as your agents go into production. Every
            plan includes the tamper-proof audit chain and deny-by-default gateway.
          </p>

          {/* Billing toggle */}
          <div className="mt-8 inline-flex items-center gap-3 rounded-full border border-[rgba(216,231,242,0.07)] bg-white/[0.03] px-4 py-2">
            <span className={`text-sm font-medium transition-colors ${!annual ? "text-white" : "text-[rgba(213,219,230,0.5)]"}`}>
              Monthly
            </span>
            <button
              onClick={() => setAnnual(!annual)}
              className={`relative h-6 w-11 rounded-full transition-colors ${annual ? "bg-[rgb(166,218,255)]" : "bg-[rgba(216,231,242,0.12)]"}`}
              aria-label="Toggle annual billing"
            >
              <span className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform ${annual ? "translate-x-5" : ""}`} />
            </button>
            <span className={`text-sm font-medium transition-colors ${annual ? "text-white" : "text-[rgba(213,219,230,0.5)]"}`}>
              Annual
            </span>
            {annual && (
              <span className="ml-1 rounded-full bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 px-2 py-0.5 text-xs font-semibold text-[rgb(166,218,255)]">
                Save 15%
              </span>
            )}
          </div>
        </motion.div>

        {/* Pricing Cards */}
        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto"
        >
          {tiers.map((tier) => {
            const isCustom = tier.monthlyPrice < 0;
            const displayPrice = isCustom
              ? "Custom"
              : tier.monthlyPrice === 0
                ? "$0"
                : `$${annual ? tier.annualPrice : tier.monthlyPrice}`;
            const period = isCustom ? "" : "/mo";

            return (
              <motion.div
                key={tier.name}
                variants={cardVariant}
                className={`relative rounded-2xl p-8 flex flex-col ${
                  tier.featured
                    ? "bg-[rgb(16,19,28)]/80 backdrop-blur-xl border-2 border-[rgb(166,218,255)]/40 shadow-[0_0_40px_rgba(166,218,255,0.08)]"
                    : "bg-[rgb(16,19,28)]/80 backdrop-blur-xl border border-[rgba(216,231,242,0.07)]"
                }`}
              >
                {tier.featured && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] text-xs font-semibold rounded-full">
                    Most Popular
                  </span>
                )}

                <h3 className="text-lg font-semibold text-white">{tier.name}</h3>
                <p className="mt-1 text-sm text-[rgba(213,219,230,0.5)]">{tier.description}</p>
                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-white">{displayPrice}</span>
                  {period && <span className="text-[rgba(213,219,230,0.5)] text-sm">{period}</span>}
                </div>
                {annual && !isCustom && tier.monthlyPrice > 0 && (
                  <p className="mt-1 text-xs text-[rgba(213,219,230,0.35)]">
                    <span className="line-through">${tier.monthlyPrice}/mo</span>{" "}
                    <span className="text-[rgb(166,218,255)]">billed ${tier.annualPrice * 12}/yr</span>
                  </p>
                )}

                <ul className="mt-8 flex-1 space-y-3">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-[rgba(213,219,230,0.6)]">
                      <span className="mt-0.5"><CheckIcon /></span>
                      {f}
                    </li>
                  ))}
                </ul>

                <a
                  href={tier.ctaHref}
                  className={`mt-8 w-full py-3 rounded-lg text-sm font-semibold transition-colors text-center block ${
                    tier.featured
                      ? "bg-[rgb(166,218,255)] text-[rgb(4,7,13)] hover:bg-[rgb(166,218,255)]/80"
                      : "border border-[rgba(216,231,242,0.12)] text-white hover:border-[rgb(166,218,255)]/40 hover:bg-white/5"
                  }`}
                >
                  {tier.cta}
                </a>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Usage Estimator */}
        <UsageEstimator />

        {/* Feature Comparison Grid */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-24"
        >
          <h3 className="text-2xl md:text-3xl font-medium text-white text-center mb-10">
            Compare plans
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full max-w-6xl mx-auto">
              <thead>
                <tr className="border-b border-[rgba(216,231,242,0.07)]">
                  <th className="py-4 px-4 text-left text-sm font-medium text-[rgba(213,219,230,0.5)] w-1/4">Feature</th>
                  <th className="py-4 px-4 text-center text-sm font-medium text-[rgba(213,219,230,0.6)]">Free</th>
                  <th className="py-4 px-4 text-center text-sm font-semibold text-[rgb(166,218,255)]">Pro</th>
                  <th className="py-4 px-4 text-center text-sm font-medium text-[rgba(213,219,230,0.6)]">Business</th>
                  <th className="py-4 px-4 text-center text-sm font-medium text-[rgba(213,219,230,0.6)]">Enterprise</th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row, i) => (
                  <tr key={row.feature} className={`border-b border-[rgba(216,231,242,0.04)] ${i % 2 === 0 ? "bg-white/[0.02]" : ""}`}>
                    <td className="py-3 px-4 text-sm text-[rgba(213,219,230,0.7)]">{row.feature}</td>
                    <td className="py-3 px-4 text-center"><span className="inline-flex justify-center"><CellValue value={row.free} /></span></td>
                    <td className="py-3 px-4 text-center"><span className="inline-flex justify-center"><CellValue value={row.pro} /></span></td>
                    <td className="py-3 px-4 text-center"><span className="inline-flex justify-center"><CellValue value={row.business} /></span></td>
                    <td className="py-3 px-4 text-center"><span className="inline-flex justify-center"><CellValue value={row.enterprise} /></span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* FAQ Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-24 max-w-3xl mx-auto"
        >
          <h3 className="text-2xl md:text-3xl font-medium text-white text-center mb-10">
            Frequently asked questions
          </h3>

          <div className="space-y-2">
            {faqs.map((faq, i) => (
              <div key={i} className="rounded-xl border border-[rgba(216,231,242,0.07)] overflow-hidden transition-colors hover:border-[rgba(216,231,242,0.15)]">
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between px-6 py-4 text-left"
                >
                  <span className="text-sm font-medium text-white pr-4">{faq.q}</span>
                  <svg
                    width="20" height="20" viewBox="0 0 20 20" fill="none"
                    className={`shrink-0 text-[rgba(213,219,230,0.5)] transition-transform duration-200 ${openFaq === i ? "rotate-180" : ""}`}
                  >
                    <path d="M5 7.5l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                {openFaq === i && (
                  <div className="px-6 pb-4">
                    <p className="text-sm text-[rgba(213,219,230,0.6)] leading-relaxed">{faq.a}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
