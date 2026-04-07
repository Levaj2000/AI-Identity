"use client";

import { useState } from "react";
import Link from "next/link";

function fmt(n: number): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function fmtDollars(n: number): string {
  return "$" + n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

const valueProps = [
  {
    title: "Per-Agent Spending Limits",
    description:
      "Set maximum spend per agent, per tool, per time period. When an agent hits its limit, requests are blocked — not just logged.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
  {
    title: "Real-Time Cost Monitoring",
    description:
      "Dashboard visibility into per-agent API costs. Alert before agents approach spending thresholds.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    title: "Fail-Closed Enforcement",
    description:
      "If an agent exceeds its budget, the gateway denies further requests. No runaway costs, no surprise bills.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
];

export default function RoiCalculator() {
  const [agents, setAgents] = useState(10);
  const [callsPerDay, setCallsPerDay] = useState(500);
  const [costPerCall, setCostPerCall] = useState(0.01);
  const [wastePercent, setWastePercent] = useState(15);
  const [runawayRisk, setRunawayRisk] = useState(5);
  const [runawayCost, setRunawayCost] = useState(5000);

  const monthlySpend = agents * callsPerDay * 30 * costPerCall;
  const monthlyWaste = monthlySpend * (wastePercent / 100);
  const monthlyRunaway = (runawayRisk / 100) * runawayCost;
  const totalMonthly = monthlySpend + monthlyWaste + monthlyRunaway;
  const annualExposure = totalMonthly * 12;
  const annualWasteSaved = monthlyWaste * 12;
  const annualRunawaySaved = monthlyRunaway * 12;
  const totalAnnualSavings = annualWasteSaved + annualRunawaySaved;

  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">ROI Calculator</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Calculate Your AI Agent{" "}
            <span className="text-[rgb(166,218,255)]">Cost Exposure</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            Autonomous agents making API calls without spending controls create
            real financial risk. See how much ungoverned API spending could cost
            your organization — and how to prevent it.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Inputs */}
          <div className="lg:col-span-3 bg-white/[0.03] border border-white/10 rounded-2xl p-6 md:p-8 space-y-7">
            <h2 className="text-xl font-bold text-white mb-1">Your Agent Fleet</h2>
            <p className="text-sm text-gray-400 mb-6">
              Adjust the inputs below to match your deployment. Results update in real time.
            </p>

            {/* Agents */}
            <InputRow
              label="AI agents in production"
              value={agents}
              onChange={setAgents}
              min={1}
              max={500}
              step={1}
            />

            {/* Calls per day */}
            <InputRow
              label="Average API calls per agent per day"
              value={callsPerDay}
              onChange={setCallsPerDay}
              min={50}
              max={10000}
              step={50}
            />

            {/* Cost per call */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-300">Average cost per API call</label>
                <span className="text-sm font-mono text-[rgb(166,218,255)]">${costPerCall.toFixed(3)}</span>
              </div>
              <input
                type="number"
                min={0.001}
                max={1}
                step={0.001}
                value={costPerCall}
                onChange={(e) => setCostPerCall(Math.max(0.001, Math.min(1, parseFloat(e.target.value) || 0.001)))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-[rgb(166,218,255)]/50 font-mono"
              />
            </div>

            {/* Waste percent */}
            <InputRow
              label="Unnecessary or redundant calls"
              description="Percentage of calls that are wasteful due to retries, duplicate requests, or unnecessary operations"
              value={wastePercent}
              onChange={setWastePercent}
              min={5}
              max={50}
              step={1}
              type="range"
              suffix="%"
            />

            {/* Runaway risk */}
            <InputRow
              label="Agent runaway incident risk per month"
              description="Probability that at least one agent enters an uncontrolled loop or makes excessive calls"
              value={runawayRisk}
              onChange={setRunawayRisk}
              min={1}
              max={25}
              step={1}
              type="range"
              suffix="%"
            />

            {/* Runaway cost */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-300">Estimated cost of a runaway incident</label>
                <span className="text-sm font-mono text-[rgb(166,218,255)]">{fmtDollars(runawayCost)}</span>
              </div>
              <p className="text-xs text-gray-500">
                The cost incurred when a single agent enters an uncontrolled spending loop
              </p>
              <input
                type="number"
                min={500}
                max={100000}
                step={500}
                value={runawayCost}
                onChange={(e) => setRunawayCost(Math.max(500, Math.min(100000, parseInt(e.target.value) || 500)))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-[rgb(166,218,255)]/50 font-mono"
              />
            </div>
          </div>

          {/* Results */}
          <div className="lg:col-span-2 space-y-6">
            {/* Exposure card */}
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 md:p-8 lg:sticky lg:top-8">
              <h2 className="text-xl font-bold text-white mb-6">Your Cost Exposure</h2>

              <div className="space-y-4 mb-8">
                <ResultLine label="Monthly API spend" value={fmtDollars(monthlySpend)} />
                <ResultLine label="Monthly waste from unnecessary calls" value={fmtDollars(monthlyWaste)} />
                <ResultLine label="Monthly expected runaway cost" value={fmtDollars(monthlyRunaway)} />
                <div className="border-t border-white/10 pt-4">
                  <ResultLine label="Total monthly exposure" value={fmtDollars(totalMonthly)} large />
                </div>
                <div className="pt-1">
                  <ResultLine label="Annual exposure" value={fmtDollars(annualExposure)} large accent />
                </div>
              </div>

              {/* Savings */}
              <div className="border-t border-white/10 pt-6">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgb(34,197,94)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                  With AI Identity Spending Controls
                </h3>
                <div className="space-y-3">
                  <SavingsLine label="Waste eliminated annually" value={fmtDollars(annualWasteSaved)} />
                  <SavingsLine label="Runaway incidents prevented" value={fmtDollars(annualRunawaySaved)} />
                  <div className="border-t border-white/10 pt-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-white">Total annual savings</span>
                      <span className="text-2xl font-extrabold text-[rgb(34,197,94)]">{fmtDollars(totalAnnualSavings)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Value Prop Cards */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">
            How AI Identity Prevents Runaway Costs
          </h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[560px] mx-auto">
            Built-in spending controls that enforce budgets at the gateway level — before costs accumulate.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {valueProps.map((d) => (
              <div
                key={d.title}
                className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 hover:border-[rgb(166,218,255)]/30 hover:bg-[rgb(166,218,255)]/[0.03] transition-all group"
              >
                <div className="w-10 h-10 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center text-[rgb(166,218,255)] mb-4 group-hover:bg-[rgb(166,218,255)]/20 transition-colors">
                  {d.icon}
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{d.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{d.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">
              Start controlling agent spend today
            </h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Set per-agent budgets, get real-time cost alerts, and prevent
              runaway incidents before they hit your bill.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <a
                href="https://dashboard.ai-identity.co"
                className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
              >
                Start Free Trial
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </a>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors"
              >
                View Pricing
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

/* ── Subcomponents ──────────────────────────────────────────────── */

function InputRow({
  label,
  description,
  value,
  onChange,
  min,
  max,
  step,
  suffix,
}: {
  label: string;
  description?: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  suffix?: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-300">{label}</label>
        <span className="text-sm font-mono text-[rgb(166,218,255)]">
          {fmt(value)}{suffix || ""}
        </span>
      </div>
      {description && <p className="text-xs text-gray-500">{description}</p>}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 rounded-full appearance-none cursor-pointer bg-white/10 accent-[rgb(166,218,255)]"
      />
      <div className="flex justify-between text-xs text-gray-600">
        <span>{fmt(min)}{suffix || ""}</span>
        <span>{fmt(max)}{suffix || ""}</span>
      </div>
    </div>
  );
}

function ResultLine({
  label,
  value,
  large,
  accent,
}: {
  label: string;
  value: string;
  large?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className={`text-sm ${large ? "font-semibold text-white" : "text-gray-400"}`}>{label}</span>
      <span
        className={
          large
            ? accent
              ? "text-2xl font-extrabold text-[rgb(166,218,255)]"
              : "text-lg font-bold text-white"
            : "text-sm font-mono text-gray-300"
        }
      >
        {value}
      </span>
    </div>
  );
}

function SavingsLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-400">{label}</span>
      <span className="text-sm font-mono text-[rgb(34,197,94)]">{value}</span>
    </div>
  );
}
