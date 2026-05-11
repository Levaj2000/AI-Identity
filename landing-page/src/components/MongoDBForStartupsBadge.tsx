import Image from "next/image";
import Link from "next/link";

/**
 * Trust signal for the MongoDB for Startups program.
 *
 * Mirrors the GoogleForStartupsBadge shape — three variants:
 *
 * - `Strip`   — wide horizontal bar with official MongoDB logo (Spring Green
 *               variant, brand-approved for dark backgrounds). Below hero
 *               or between sections.
 * - `Compact` — single-line text link. Footer / pricing CTA.
 * - `Inline`  — bare-text mention with link. Body copy on About / Architecture.
 *
 * Compact + Inline stay text-only because they appear in sentence-fragment
 * contexts where a logo would feel out of place. The Strip carries the
 * visual weight.
 */

const PROGRAM_URL = "https://www.mongodb.com/startups";
const LOGO_PATH = "/images/partners/mongodb-logo-spring-green.png";

export function MongoDBForStartupsStrip({ className = "" }: { className?: string }) {
  return (
    <section
      className={`w-full py-10 px-6 border-y border-[rgba(216,231,242,0.05)] bg-[rgba(166,218,255,0.02)] ${className}`}
      aria-label="Part of the MongoDB for Startups program"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8">
        <p className="text-xs uppercase tracking-[0.2em] text-[rgba(213,219,230,0.55)]">
          Part of
        </p>
        <Link
          href={PROGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center transition-opacity hover:opacity-80"
          aria-label="MongoDB for Startups"
        >
          <Image
            src={LOGO_PATH}
            alt="MongoDB"
            width={180}
            height={45}
            className="h-9 w-auto"
            priority={false}
          />
          <span className="ml-3 text-sm text-[rgba(213,219,230,0.7)]">
            for Startups
          </span>
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
