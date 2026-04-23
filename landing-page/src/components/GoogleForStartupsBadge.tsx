import Link from "next/link";

/**
 * Trust signal for the Google for Startups Cloud Program.
 *
 * Three variants tuned for different placements:
 *
 * - `Strip`   — wide horizontal "Supported by" bar. Use below hero
 *               or between major page sections.
 * - `Compact` — single-line link. Footer / pricing CTA.
 * - `Inline`  — bare-text mention with link. Body copy on About.
 *
 * Why text-only: Google has strict trademark rules around their
 * marks and the official "Google for Startups" badge artwork.
 * Reconstructing the Google "G" inline risks a brand complaint.
 * Plain-text + link to the program page is brand-safe and renders
 * cleanly without depending on an asset file.
 *
 * To add the official badge: download the supplied SVG from the
 * program portal (https://startup.google.com), drop it at
 * `public/images/google-for-startups-badge.svg`, then swap any of
 * these variants for an `<Image src="/images/google-for-startups-badge.svg" .../>`.
 * The link wrapper + program URL stay the same.
 */

const PROGRAM_URL = "https://cloud.google.com/startup";

export function GoogleForStartupsStrip({ className = "" }: { className?: string }) {
  return (
    <section
      className={`w-full py-8 px-6 border-y border-[rgba(216,231,242,0.05)] bg-[rgba(166,218,255,0.02)] ${className}`}
      aria-label="Backed by Google for Startups Cloud Program"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-6">
        <p className="text-xs uppercase tracking-[0.2em] text-[rgba(213,219,230,0.55)]">
          Supported by
        </p>
        <Link
          href={PROGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-base sm:text-lg font-medium text-[rgba(213,219,230,0.9)] hover:text-white transition-colors"
        >
          Google for Startups Cloud Program
        </Link>
      </div>
    </section>
  );
}

export function GoogleForStartupsCompact({ className = "" }: { className?: string }) {
  return (
    <Link
      href={PROGRAM_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center text-xs text-[rgba(213,219,230,0.55)] hover:text-white transition-colors ${className}`}
    >
      Supported by Google for Startups
    </Link>
  );
}

export function GoogleForStartupsInline({ className = "" }: { className?: string }) {
  return (
    <span className={className}>
      AI Identity is a{" "}
      <Link
        href={PROGRAM_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[rgb(166,218,255)] hover:underline"
      >
        Google for Startups Cloud Program
      </Link>{" "}
      portfolio company.
    </span>
  );
}
