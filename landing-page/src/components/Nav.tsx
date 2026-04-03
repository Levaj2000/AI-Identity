"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

const navLinks = [
  { label: "Home", path: "/" },
  { label: "How It Works", path: "/how-it-works" },
  { label: "Security", path: "/security" },
  { label: "Pricing", path: "/pricing" },
  { label: "Blog", path: "/blog" },
  { label: "About", path: "/about" },
  { label: "Docs", path: "/docs" },
];

const solutionLinks = [
  { label: "Customer Support Agents", path: "/use-cases/customer-support" },
  { label: "Coding Assistants", path: "/use-cases/coding-assistant" },
  { label: "Financial Compliance", path: "/use-cases/financial-compliance" },
  { label: "divider", path: "" },
  { label: "EU AI Act Checklist", path: "/eu-ai-act-checklist" },
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
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span className="text-white font-semibold text-lg">AI Identity</span>
        </Link>

        {/* Desktop Links */}
        <div className="hidden md:flex items-center gap-8">
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
          <a
            href="https://dashboard.ai-identity.co"
            className="hidden md:inline-flex px-4 py-2 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 text-[rgb(166,218,255)] text-sm font-medium hover:bg-[rgb(166,218,255)]/20 transition-colors"
          >
            Get Started
          </a>
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden text-white p-2"
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

      {/* Mobile Menu */}
      {mobileOpen && (
        <div id="mobile-nav" className="md:hidden bg-[rgb(4,7,13)] border-t border-white/5 px-6 py-4 space-y-3">
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
          <a
            href="https://dashboard.ai-identity.co"
            className="block w-full text-center px-4 py-2 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 text-[rgb(166,218,255)] text-sm font-medium mt-2"
          >
            Get Started
          </a>
        </div>
      )}
    </nav>
  );
}
