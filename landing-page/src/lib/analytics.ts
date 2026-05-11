/**
 * Probe-page analytics helpers.
 *
 * Pageviews + referrer + UTM are captured automatically by Vercel Web Analytics
 * via <Analytics /> mounted in app/layout.tsx — no per-page wiring required.
 *
 * This module wraps the custom-event API used for conversions we care about
 * specifically for the strategy-checkpoint probe reviews (Milestone #47,
 * Decision #45). When a probe form converts, call trackEmailCapture() with the
 * probe slug; the kill-review dashboards then have per-probe counts to compare
 * against the written kill criteria.
 *
 * Usage:
 *   import { trackEmailCapture } from "@/lib/analytics";
 *   trackEmailCapture("pqc-readiness", { source: "linkedin" });
 */
import { track } from "@vercel/analytics";

/**
 * Stable slug for each demand probe. Adding a new probe? Add a slug here
 * and the kill-review queries already know how to filter on it.
 */
export type ProbeSlug =
  | "ai-forensics-standalone"   // Probe 1 — Milestone #48
  | "pqc-readiness"             // Probe 2 — Milestone #49
  | "finance-compliance-pack"   // Probe 3 — Milestone #50
  | "newsletter";               // Pre-existing Footer Buttondown signup

interface EmailCaptureProps {
  /** Where the visitor came from. Free-text, captured before form submit. */
  source?: string;
}

/**
 * Fire when a probe form successfully captures an email (waitlist, gated
 * download, etc.). Wire this into the form's success branch — NOT the click
 * handler — so we only count actual conversions.
 *
 * The Vercel Analytics dashboard exposes these as named events with the
 * `probe` and `source` properties filterable in custom views.
 */
export function trackEmailCapture(
  probe: ProbeSlug,
  props: EmailCaptureProps = {},
): void {
  track("email_captured", {
    probe,
    source: props.source ?? "direct",
  });
}

/**
 * Fire when a probe artifact is actually opened/downloaded. For the PQC
 * Readiness whitepaper this fires when the download link is clicked
 * post-email-capture; the difference between captures and downloads tells
 * us whether the form is creating phantom leads (typed wrong email and
 * bounced).
 */
export function trackProbeDownload(probe: ProbeSlug, artifact: string): void {
  track("probe_download", { probe, artifact });
}
