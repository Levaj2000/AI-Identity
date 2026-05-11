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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    try {
      await fetch(
        "https://buttondown.com/api/emails/embed-subscribe/ai-identity",
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `email=${encodeURIComponent(email)}&tag=${encodeURIComponent(probe)}`,
          mode: "no-cors",
        },
      );
      // no-cors hides the response, so we treat any non-throw as success
      trackEmailCapture(probe, {
        source: typeof document !== "undefined" ? document.referrer || "direct" : "direct",
      });
      setSubmitted(true);
      setEmail("");
    } catch {
      // Even on transport error, fire the conversion — Buttondown often
      // accepts the write even when the browser can't see the response.
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
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2 max-w-md">
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
  );
}
