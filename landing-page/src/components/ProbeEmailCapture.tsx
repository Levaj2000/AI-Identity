"use client";

import { useState } from "react";
import { trackEmailCapture, type ProbeSlug } from "@/lib/analytics";

interface ProbeEmailCaptureProps {
  /** Probe slug used by analytics — also the kill-review segmentation key. */
  probe: ProbeSlug;
  /** Label above the input. Tailor to the probe — "Join the waitlist", "Get the whitepaper", etc. */
  label: string;
  /** Button text. Match the value being exchanged. */
  cta: string;
  /** Optional placeholder. Defaults to "you@company.com". */
  placeholder?: string;
  /** Optional success message override. Defaults to "Thanks — we'll be in touch." */
  successMessage?: string;
}

/**
 * Reusable email-capture form for the demand-probe landing pages.
 *
 * Posts to the same Buttondown list as the Footer newsletter — single source
 * of truth for emails. Conversion segmentation happens via the analytics
 * event (probe + source props) rather than via separate Buttondown lists.
 *
 * Always fires trackEmailCapture on the success branch so the Vercel
 * Analytics dashboard has per-probe counts for the 30-day kill reviews.
 */
export default function ProbeEmailCapture({
  probe,
  label,
  cta,
  placeholder = "you@company.com",
  successMessage = "Thanks — we'll be in touch.",
}: ProbeEmailCaptureProps) {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    setError(null);
    const source =
      typeof document !== "undefined" ? document.referrer || "direct" : "direct";
    try {
      const res = await fetch("/api/probe-signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, probe, source }),
      });

      if (res.status === 200 || res.status === 202) {
        trackEmailCapture(probe, { source });
        setSubmitted(true);
        setEmail("");
      } else if (res.status === 400) {
        setError("Please enter a valid email address.");
      } else if (res.status === 429) {
        setError("You're going a little fast — please try again in a moment.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } catch {
      // Transport error (offline, blocked, etc). Still fire the conversion
      // event so probe signal isn't lost — the user retried and the email
      // is gone, but the analytics dashboard remains the source of truth
      // for kill-criteria counts.
      trackEmailCapture(probe, { source: "fallback" });
      setSubmitted(true);
      setEmail("");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <p className="text-sm text-[rgb(166,218,255)]" role="status">
        {successMessage}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-1.5 w-full max-w-md">
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2 w-full">
        <label htmlFor={`probe-email-${probe}`} className="sr-only">
          {label}
        </label>
        <input
          id={`probe-email-${probe}`}
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={placeholder}
          aria-label={label}
          className="flex-1 px-4 py-2.5 rounded-lg bg-[rgb(16,19,28)] border border-[rgba(216,231,242,0.07)] text-sm text-white placeholder-[rgba(213,219,230,0.4)] focus:outline-none focus:border-[rgb(166,218,255)]/40"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-5 py-2.5 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 text-[rgb(166,218,255)] text-sm font-medium hover:bg-[rgb(166,218,255)]/20 transition-colors disabled:opacity-50"
        >
          {loading ? "..." : cta}
        </button>
      </form>
      {error && (
        <p className="text-xs text-red-400 font-medium pl-1" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
