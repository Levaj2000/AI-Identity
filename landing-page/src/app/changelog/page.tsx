import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";

export const metadata: Metadata = generatePageMetadata({
  title: "Changelog — AI Identity",
  description:
    "See what's new in AI Identity. Product updates, new features, and improvements to AI agent governance infrastructure.",
  path: "/changelog",
});

type ChangelogEntry = {
  version: string;
  date: string;
  type: "feature" | "enhancement" | "bugfix" | "infrastructure";
  title: string;
  items: string[];
};

const changelog: ChangelogEntry[] = [
  {
    version: "0.2.0",
    date: "April 6, 2026",
    type: "feature",
    title: "AI Forensics Pillar & Launch Prep",
    items: [
      "AI Forensics elevated to first-class product pillar with dedicated landing page",
      "Four Pillars governance framework added to homepage (Identity, Policy, Compliance, Forensics)",
      "Healthcare and Finance industry pages added to Solutions navigation",
      "Automated 90-day inactive free-tier user cleanup",
      "QA smoke test cleanup hardened with retry logic and HTTP status verification",
      "Admin agent drawer items now clickable with links to agent detail pages",
      "Test user purge utility for database hygiene",
    ],
  },
  {
    version: "0.1.0",
    date: "March 29, 2026",
    type: "feature",
    title: "Foundation Release",
    items: [
      "Per-agent identity with scoped API keys and lifecycle management",
      "HMAC-SHA256 tamper-proof audit trail with chain verification",
      "Deny-by-default gateway with fail-closed policy enforcement",
      "Interactive API Playground for live demo",
      "Admin dashboard with user management, agent overview, and system health",
      "QA Checklist with 15-step E2E production validation",
      "Forensics dashboard with incident replay, anomaly detection, and export",
      "Compliance page with automated assessments",
      "Shadow agent detection for unregistered agent monitoring",
      "EU AI Act Checklist page",
      "Blog: Introducing AI Forensics, Why AI Agents Need Identity, Compliance in the Age of Autonomous AI",
    ],
  },
];

const typeColors: Record<string, { bg: string; text: string; label: string }> = {
  feature: { bg: "bg-[rgb(166,218,255)]/10", text: "text-[rgb(166,218,255)]", label: "Feature" },
  enhancement: { bg: "bg-green-500/10", text: "text-green-400", label: "Enhancement" },
  bugfix: { bg: "bg-amber-500/10", text: "text-amber-400", label: "Bug Fix" },
  infrastructure: { bg: "bg-purple-500/10", text: "text-purple-400", label: "Infrastructure" },
};

export default function Changelog() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Changelog</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            What&apos;s New in{" "}
            <span className="text-[rgb(166,218,255)]">AI Identity</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            Product updates, new features, and improvements to AI agent governance infrastructure.
          </p>
        </div>
      </section>

      {/* Changelog Timeline */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-[7px] top-2 bottom-2 w-px bg-white/10 hidden md:block" />

            <div className="space-y-12">
              {changelog.map((entry) => {
                const typeStyle = typeColors[entry.type] || typeColors.feature;
                return (
                  <div key={entry.version} className="relative md:pl-10">
                    {/* Dot on timeline */}
                    <div className="absolute left-0 top-2 w-[15px] h-[15px] rounded-full bg-[rgb(166,218,255)]/20 border-2 border-[rgb(166,218,255)] hidden md:block" />

                    <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 hover:border-[rgb(166,218,255)]/20 transition-colors">
                      {/* Header */}
                      <div className="flex flex-wrap items-center gap-3 mb-4">
                        <span className="text-sm font-mono font-semibold text-white bg-white/10 px-3 py-1 rounded-lg">
                          v{entry.version}
                        </span>
                        <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${typeStyle.bg} ${typeStyle.text}`}>
                          {typeStyle.label}
                        </span>
                        <span className="text-sm text-gray-500 ml-auto">
                          {entry.date}
                        </span>
                      </div>

                      {/* Title */}
                      <h2 className="text-lg font-semibold text-white mb-4">
                        {entry.title}
                      </h2>

                      {/* Items */}
                      <ul className="space-y-2">
                        {entry.items.map((item, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-400 leading-relaxed">
                            <span className="text-[rgb(166,218,255)] shrink-0 mt-0.5">+</span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
