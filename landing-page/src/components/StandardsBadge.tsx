import Link from "next/link";

/**
 * Trust signal for AI Identity's open-standards work — the strongest,
 * most differentiated credibility asset the company has.
 *
 * Honesty guardrails (do not loosen without checking the actual schema state):
 *  - Say "Contributing to OCSF", NOT "merged into". Only `serialization_id`
 *    (PR #1662) is merged upstream; `ai_agent` (#1641) and `attestation`
 *    (#1661) are still in review. "Contributing to" stays true regardless.
 *  - CoSAI WS4 = Coalition for Secure AI, Agentic IAM workstream (OASIS).
 *    Jeff participates; framing is "member", not "co-lead".
 *
 * Why this matters: this is the EQTY "partner logos" equivalent, except
 * it's real, current, and uniquely ours. EQTY anchors on hardware vendors;
 * we anchor on open standards anyone can verify against.
 *
 * Variants mirror GoogleForStartupsBadge:
 *  - `Strip`   — wide horizontal band. Use directly below the hero.
 *  - `Compact` — single-line link for footer / dense placements.
 */

const OCSF_URL = "https://ocsf.io";
const COSAI_URL = "https://www.coalitionforsecureai.org";

export function StandardsStrip({ className = "" }: { className?: string }) {
  return (
    <section
      className={`w-full py-8 px-6 border-y border-[rgba(216,231,242,0.05)] bg-[rgba(166,218,255,0.02)] ${className}`}
      aria-label="AI Identity's open-standards contributions"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col items-center gap-5">
        <p className="text-xs uppercase tracking-[0.2em] text-[rgba(213,219,230,0.55)]">
          Built on open standards
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-12">
          {/* OCSF */}
          <Link
            href={OCSF_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-3 text-center sm:text-left"
          >
            <span className="text-base sm:text-lg font-medium text-[rgba(213,219,230,0.9)] group-hover:text-white transition-colors whitespace-nowrap">
              Contributing to OCSF
            </span>
            <span className="hidden sm:inline text-sm text-[rgba(213,219,230,0.5)]">
              the open schema for security telemetry
            </span>
          </Link>

          {/* Divider */}
          <span className="hidden sm:block w-px h-6 bg-[rgba(216,231,242,0.12)]" aria-hidden="true" />

          {/* CoSAI WS4 */}
          <Link
            href={COSAI_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-3 text-center sm:text-left"
          >
            <span className="text-base sm:text-lg font-medium text-[rgba(213,219,230,0.9)] group-hover:text-white transition-colors whitespace-nowrap">
              CoSAI WS4
            </span>
            <span className="hidden sm:inline text-sm text-[rgba(213,219,230,0.5)]">
              Coalition for Secure AI — Agentic Identity &amp; Access
            </span>
          </Link>
        </div>
      </div>
    </section>
  );
}

export function StandardsCompact({ className = "" }: { className?: string }) {
  return (
    <Link
      href={OCSF_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center text-xs text-[rgba(213,219,230,0.55)] hover:text-white transition-colors ${className}`}
    >
      Contributing to OCSF &amp; CoSAI WS4
    </Link>
  );
}
