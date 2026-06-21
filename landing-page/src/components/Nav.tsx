"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

const navLinks = [
  { label: "Forensics", path: "/forensics" },
  { label: "Spec", path: "/spec" },
  { label: "Product", path: "/product" },
  { label: "Pricing", path: "/pricing" },
  { label: "Blog", path: "/blog" },
  { label: "About", path: "/about" },
];

const solutionLinks = [
  { label: "Customer Support Agents", path: "/use-cases/customer-support" },
  { label: "Coding Assistants", path: "/use-cases/coding-assistant" },
  { label: "Financial Compliance", path: "/use-cases/financial-compliance" },
  { label: "divider", path: "" },
  { label: "Healthcare", path: "/industries/healthcare" },
  { label: "Finance", path: "/industries/finance" },
  { label: "divider", path: "" },
  { label: "EU AI Act Checklist", path: "/eu-ai-act-checklist" },
  { label: "ROI Calculator", path: "/roi-calculator" },
  { label: "divider", path: "" },
  { label: "vs Opal Security", path: "/vs/opal" },
  { label: "vs Valence Security", path: "/vs/valence" },
  { label: "vs Holistic AI", path: "/vs/holistic-ai" },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [solutionsOpen, setSolutionsOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
    setSolutionsOpen(false);
  }, [pathname]);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? "bg-[rgb(4,7,13)]/90 backdrop-blur-xl border-b border-white/5" : "bg-transparent"
    }`}>
      <div className="max-w-[1200px] mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5" aria-label="AI Identity — home">
          {/* Inline SVG of the new shield + Ai mark. Keeping it inline rather than
              <img src=…> so it loads with the document and scales cleanly at any DPR. */}
          <svg
            width="32" height="35" viewBox="0 0 200 220"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true" focusable="false"
            className="shrink-0"
          >
            <defs>
              <linearGradient id="nav-shield" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#5BA0DC" />
                <stop offset="0.5" stopColor="#3A86C8" />
                <stop offset="1" stopColor="#1F5694" />
              </linearGradient>
              <linearGradient id="nav-letter" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#7CB6E2" />
                <stop offset="0.6" stopColor="#3A86C8" />
                <stop offset="1" stopColor="#1F5694" />
              </linearGradient>
              {/* Brighter gradient for the "i" — keeps it readable at favicon size */}
              <linearGradient id="nav-letter-bright" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#C5E3F7" />
                <stop offset="0.6" stopColor="#7CB6E2" />
                <stop offset="1" stopColor="#5BA0DC" />
              </linearGradient>
            </defs>
            <path
              d="M30 22 C30 13 38 8 47 8 L153 8 C162 8 170 13 170 22 L170 110 C170 158 138 192 100 210 C62 192 30 158 30 110 Z M45 32 C45 27 49 24 54 24 L146 24 C151 24 155 27 155 32 L155 108 C155 150 124 178 100 191 C76 178 45 150 45 108 Z"
              fill="url(#nav-shield)"
              fillRule="evenodd"
            />
            <path
              d="M62 156 L88 60 L106 60 L132 156 L117 156 L110 130 L84 130 L77 156 Z M87 116 L107 116 L97 78 Z"
              fill="url(#nav-letter)"
              fillRule="evenodd"
            />
            <rect x="141" y="92" width="11" height="64" rx="1.5" fill="url(#nav-letter-bright)" />
            <circle cx="146.5" cy="80" r="6.5" fill="url(#nav-letter-bright)" />
          </svg>
          <span className="text-white font-semibold text-lg tracking-tight">AI Identity</span>
        </Link>

        {/* Desktop Links — show at lg+ (1024px). At md (768px) the 10+ items
            don't fit alongside the wordmark + CTA, so we use the mobile menu.
            ml-6 keeps a guaranteed gap between the wordmark and the first link
            at narrow lg widths (1024-1280) where the nav is otherwise edge-to-edge. */}
        <div className="hidden lg:flex items-center gap-6 xl:gap-8 ml-6">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              href={link.path}
              className={`text-sm transition-colors ${
                pathname === link.path
                  ? "text-white"
                  : "text-[rgba(213,219,230,0.7)] hover:text-white"
              }`}
            >
              {link.label}
            </Link>
          ))}
          {/* Solutions dropdown */}
          <div
            className="relative"
            onMouseEnter={() => setSolutionsOpen(true)}
            onMouseLeave={() => setSolutionsOpen(false)}
            onBlur={(e) => {
              // Close when keyboard focus leaves the Solutions block entirely
              // (tabbing past the last submenu link), not on focus moves within it.
              if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                setSolutionsOpen(false);
              }
            }}
          >
            <button
              aria-haspopup="menu"
              aria-expanded={solutionsOpen}
              aria-controls="solutions-menu"
              onClick={() => setSolutionsOpen(!solutionsOpen)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setSolutionsOpen(false);
              }}
              className={`text-sm transition-colors flex items-center gap-1 ${
                pathname.startsWith("/use-cases") || pathname === "/eu-ai-act-checklist"
                  ? "text-white"
                  : "text-[rgba(213,219,230,0.7)] hover:text-white"
              }`}
            >
              Solutions
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" className={`mt-0.5 transition-transform ${solutionsOpen ? "rotate-180" : ""}`}>
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
            <div
              id="solutions-menu"
              role="menu"
              aria-label="Solutions submenu"
              className={`absolute top-full left-1/2 -translate-x-1/2 pt-2 transition-all duration-200 ${
                solutionsOpen ? "opacity-100 visible" : "opacity-0 invisible"
              }`}
            >
              <div className="bg-[rgb(16,19,28)] border border-white/10 rounded-xl py-2 min-w-[220px] shadow-xl shadow-black/40">
                {solutionLinks.map((link, i) =>
                  link.label === "divider" ? (
                    <div key={`divider-${i}`} className="my-1 border-t border-white/5" role="separator" />
                  ) : (
                    <Link
                      key={link.path}
                      href={link.path}
                      role="menuitem"
                      onKeyDown={(e) => {
                        if (e.key === "Escape") setSolutionsOpen(false);
                      }}
                      className={`block px-4 py-2.5 text-sm transition-colors ${
                        pathname === link.path
                          ? "text-[rgb(166,218,255)] bg-[rgb(166,218,255)]/5"
                          : "text-[rgba(213,219,230,0.7)] hover:text-white hover:bg-white/[0.03]"
                      }`}
                    >
                      {link.label}
                    </Link>
                  )
                )}
              </div>
            </div>
          </div>
          <a
            href="https://dashboard.ai-identity.co"
            className="text-sm text-[rgba(213,219,230,0.7)] hover:text-white transition-colors"
          >
            Dashboard
          </a>
        </div>

        {/* CTA + Mobile Toggle */}
        <div className="flex items-center gap-4">
          <Link
            href="/contact?intent=design-partner"
            className="hidden lg:inline-flex px-4 py-2 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 text-[rgb(166,218,255)] text-sm font-medium hover:bg-[rgb(166,218,255)]/20 transition-colors"
          >
            Design Partner
          </Link>
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="lg:hidden text-white p-2"
            aria-label="Toggle menu"
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              {mobileOpen ? (
                <>
                  <path d="M18 6L6 18" />
                  <path d="M6 6l12 12" />
                </>
              ) : (
                <>
                  <path d="M3 12h18" />
                  <path d="M3 6h18" />
                  <path d="M3 18h18" />
                </>
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile / tablet menu — shown below lg breakpoint */}
      {mobileOpen && (
        <div id="mobile-nav" className="lg:hidden bg-[rgb(4,7,13)] border-t border-white/5 px-6 py-4 space-y-3">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              href={link.path}
              className={`block text-sm py-2 ${
                pathname === link.path
                  ? "text-white"
                  : "text-[rgba(213,219,230,0.7)]"
              }`}
            >
              {link.label}
            </Link>
          ))}
          <div className="py-2">
            <span className="text-sm text-white font-medium">Solutions</span>
            <div className="mt-1 ml-3 space-y-1">
              {solutionLinks.map((link, i) =>
                link.label === "divider" ? (
                  <div key={`divider-${i}`} className="my-1 border-t border-white/5" />
                ) : (
                  <Link
                    key={link.path}
                    href={link.path}
                    className={`block text-sm py-1.5 ${
                      pathname === link.path
                        ? "text-[rgb(166,218,255)]"
                        : "text-[rgba(213,219,230,0.5)]"
                    }`}
                  >
                    {link.label}
                  </Link>
                )
              )}
            </div>
          </div>
          <a
            href="https://dashboard.ai-identity.co"
            className="block text-sm py-2 text-[rgba(213,219,230,0.7)]"
          >
            Dashboard
          </a>
          <Link
            href="/contact?intent=design-partner"
            className="block w-full text-center px-4 py-2 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 text-[rgb(166,218,255)] text-sm font-medium mt-2"
          >
            Design Partner
          </Link>
        </div>
      )}
    </nav>
  );
}
