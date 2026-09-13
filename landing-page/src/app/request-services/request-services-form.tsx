"use client";

import { useState } from "react";

const SERVICES = [
  {
    id: "intro-call",
    name: "Intro Call",
    price: "$150",
    blurb: "30 minutes with Jeff. Credited toward any engagement.",
  },
  {
    id: "evidence-review",
    name: "Evidence Architecture Review",
    price: "$750",
    blurb:
      "Fixed-scope review of how you built (or are building) your agent audit trail. You get a gap report against OCSF, EU AI Act, and California expectations. A review — not a verification.",
  },
  {
    id: "build-advisory",
    name: "Verifiable Build Advisory",
    price: "$1,500/mo",
    blurb: "Ongoing advisory while your team builds: design reviews and weekly working sessions.",
  },
  {
    id: "verifier-enablement",
    name: "Verifier Enablement",
    price: "$2,500",
    blurb:
      "For audit firms preparing for California's verifier market: training on the evidence standards plus tooling.",
  },
] as const;

const GOALS = [
  "Build a verifiable agent system",
  "Prepare for an audit or regulation",
  "Evaluate the AI Identity platform",
  "Train my audit team",
  "Something else",
];

const TIMELINES = ["ASAP", "Within a month", "1–3 months", "Just exploring"];

const BUDGETS = ["$150–$500", "$500–$2,000", "$2,000–$5,000", "$5,000+"];

const inputClass =
  "w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white placeholder:text-gray-600 focus:border-[rgb(166,218,255)]/60 focus:outline-none";

const labelClass = "block text-sm font-medium text-gray-300 mb-2";

type Status = "idle" | "sending" | "sent" | "error";

export default function RequestServicesForm() {
  const [service, setService] = useState<string>("intro-call");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string>("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setStatus("sending");

    const form = e.currentTarget;
    const data = new FormData(form);
    const paidAcknowledged = data.get("paidAcknowledged") === "on";

    if (!paidAcknowledged) {
      setStatus("idle");
      setError("Please confirm you understand advisory engagements are paid.");
      return;
    }

    try {
      const res = await fetch("/api/service-request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: data.get("name"),
          email: data.get("email"),
          company: data.get("company"),
          role: data.get("role"),
          service,
          goal: data.get("goal"),
          timeline: data.get("timeline"),
          budget: data.get("budget"),
          description: data.get("description"),
          heardAbout: data.get("heardAbout"),
          website: data.get("website"),
          paidAcknowledged: true,
        }),
      });

      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (body.error === "rate_limited") {
          throw new Error("Too many requests. Please try again in an hour.");
        }
        throw new Error("Something went wrong sending your request. Please try again.");
      }
      if (body.delivered !== true) {
        throw new Error(
          "Your request could not be delivered right now. Please email jeff@ai-identity.co directly."
        );
      }
      setStatus("sent");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    }
  }

  if (status === "sent") {
    return (
      <div className="rounded-2xl border border-[rgb(166,218,255)]/20 bg-[rgb(166,218,255)]/5 p-8 text-center">
        <h3 className="text-xl font-bold text-white mb-3">Request received</h3>
        <p className="text-sm text-gray-400 max-w-[520px] mx-auto leading-relaxed">
          Thanks — your request is on its way to Jeff. He reads every one personally and
          replies with an honest read on whether he can help. If your situation is
          time-sensitive, email{" "}
          <a
            href="mailto:jeff@ai-identity.co"
            className="text-[rgb(166,218,255)] hover:underline"
          >
            jeff@ai-identity.co
          </a>{" "}
          directly.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="relative space-y-8">
      {/* Service selection */}
      <div>
        <span className={labelClass}>Which service do you need? *</span>
        <div className="grid sm:grid-cols-2 gap-3">
          {SERVICES.map((s) => {
            const selected = service === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setService(s.id)}
                aria-pressed={selected}
                className={`text-left rounded-xl border p-5 transition-colors ${
                  selected
                    ? "border-[rgb(166,218,255)]/60 bg-[rgb(166,218,255)]/5"
                    : "border-white/10 bg-white/[0.03] hover:border-white/25"
                }`}
              >
                <div className="flex items-baseline justify-between gap-2 mb-1">
                  <span className="font-semibold text-white text-sm">{s.name}</span>
                  <span className="text-[rgb(166,218,255)] font-semibold text-sm whitespace-nowrap">
                    {s.price}
                  </span>
                </div>
                <p className="text-sm text-gray-400 leading-relaxed">{s.blurb}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Contact */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="rs-name" className={labelClass}>
            Full name *
          </label>
          <input id="rs-name" name="name" required maxLength={120} className={inputClass} autoComplete="name" />
        </div>
        <div>
          <label htmlFor="rs-email" className={labelClass}>
            Work email *
          </label>
          <input
            id="rs-email"
            name="email"
            type="email"
            required
            maxLength={254}
            className={inputClass}
            autoComplete="email"
          />
        </div>
        <div>
          <label htmlFor="rs-company" className={labelClass}>
            Company *
          </label>
          <input id="rs-company" name="company" required maxLength={160} className={inputClass} autoComplete="organization" />
        </div>
        <div>
          <label htmlFor="rs-role" className={labelClass}>
            Role / title
          </label>
          <input id="rs-role" name="role" maxLength={120} className={inputClass} autoComplete="organization-title" />
        </div>
      </div>

      {/* Context */}
      <div className="grid sm:grid-cols-3 gap-4">
        <div>
          <label htmlFor="rs-goal" className={labelClass}>
            What are you trying to do?
          </label>
          <select id="rs-goal" name="goal" className={inputClass} defaultValue="">
            <option value="" disabled>
              Select…
            </option>
            {GOALS.map((g) => (
              <option key={g} value={g} className="bg-[#0b0f16]">
                {g}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="rs-timeline" className={labelClass}>
            Timeline
          </label>
          <select id="rs-timeline" name="timeline" className={inputClass} defaultValue="">
            <option value="" disabled>
              Select…
            </option>
            {TIMELINES.map((t) => (
              <option key={t} value={t} className="bg-[#0b0f16]">
                {t}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="rs-budget" className={labelClass}>
            Budget range
          </label>
          <select id="rs-budget" name="budget" className={inputClass} defaultValue="">
            <option value="" disabled>
              Select…
            </option>
            {BUDGETS.map((b) => (
              <option key={b} value={b} className="bg-[#0b0f16]">
                {b}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="rs-description" className={labelClass}>
          Briefly describe what you need *
        </label>
        <textarea
          id="rs-description"
          name="description"
          required
          rows={5}
          maxLength={4000}
          placeholder="What are your agents doing, and what question can't you currently answer?"
          className={inputClass}
        />
      </div>

      <div>
        <label htmlFor="rs-heard" className={labelClass}>
          How did you hear about us?
        </label>
        <input id="rs-heard" name="heardAbout" maxLength={300} className={inputClass} />
      </div>

      {/*
        Honeypot. Humans never see this field; generic form-spam bots fill
        every input they find. A populated value makes the API route drop the
        submission while still answering success, so the bot learns nothing.
        Kept off-screen rather than display:none so it survives bots that
        skip hidden inputs, and excluded from tab order, autofill, and AT.
      */}
      <div
        aria-hidden="true"
        className="absolute -left-[9999px] top-auto h-px w-px overflow-hidden"
      >
        <label htmlFor="rs-website">Website</label>
        <input
          id="rs-website"
          name="website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          defaultValue=""
        />
      </div>

      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          name="paidAcknowledged"
          className="mt-1 h-4 w-4 accent-[rgb(166,218,255)]"
        />
        <span className="text-sm text-gray-300 leading-relaxed">
          I understand AI Identity advisory engagements are paid services. *
        </span>
      </label>

      {error && (
        <p role="alert" className="text-sm text-red-400">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={status === "sending"}
        className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors disabled:opacity-50"
      >
        {status === "sending" ? "Sending…" : "Submit request"}
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </button>
    </form>
  );
}
