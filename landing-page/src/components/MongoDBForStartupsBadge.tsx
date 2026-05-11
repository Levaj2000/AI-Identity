import Link from "next/link";

/**
 * Trust signal for the MongoDB for Startups program.
 *
 * Mirrors the GoogleForStartupsBadge shape — three variants:
 *
 * - `Strip`   — wide horizontal bar. Use below hero or between sections.
 * - `Compact` — single-line link. Footer / pricing CTA.
 * - `Inline`  — bare-text mention with link. Body copy on About / Architecture.
 *
 * Text-only by default: MongoDB has brand-asset guidelines and we don't
 * want a takedown over an unofficial reproduction of their leaf mark.
 * The official badge artwork lives in the MongoDB for Startups portal —
 * drop the supplied SVG at `public/images/mongodb-for-startups-badge.svg`
 * and swap any of these variants for an `<Image>` tag pointing at it.
 */

const PROGRAM_URL = "https://www.mongodb.com/startups";

export function MongoDBForStartupsStrip({ className = "" }: { className?: string }) {
  return (
    <section
      className={`w-full py-8 px-6 border-y border-[rgba(216,231,242,0.05)] bg-[rgba(166,218,255,0.02)] ${className}`}
      aria-label="Part of the MongoDB for Startups program"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-6">
        <p className="text-xs uppercase tracking-[0.2em] text-[rgba(213,219,230,0.55)]">
          Part of
        </p>
        <Link
          href={PROGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-base sm:text-lg font-medium text-[rgba(213,219,230,0.9)] hover:text-white transition-colors"
        >
          MongoDB for Startups
        </Link>
      </div>
    </section>
  );
}

export function MongoDBForStartupsCompact({ className = "" }: { className?: string }) {
  return (
    <Link
      href={PROGRAM_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center text-xs text-[rgba(213,219,230,0.55)] hover:text-white transition-colors ${className}`}
    >
      Part of MongoDB for Startups
    </Link>
  );
}

export function MongoDBForStartupsInline({ className = "" }: { className?: string }) {
  return (
    <span className={className}>
      AI Identity is part of{" "}
      <Link
        href={PROGRAM_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[rgb(166,218,255)] hover:underline"
      >
        MongoDB for Startups
      </Link>
      .
    </span>
  );
}
