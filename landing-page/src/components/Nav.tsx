import { Link, useLocation } from "react-router";
import { useState, useEffect } from "react";

const navLinks = [
  { label: "Home", path: "/" },
  { label: "How It Works", path: "/how-it-works" },
  { label: "Security", path: "/security" },
  { label: "Pricing", path: "/pricing" },
  { label: "Blog", path: "/blog" },
  { label: "Docs", path: "/docs" },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? "bg-[rgb(4,7,13)]/90 backdrop-blur-xl border-b border-white/5" : "bg-transparent"
    }`}>
      <div className="max-w-[1200px] mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
              to={link.path}
              className={`text-sm transition-colors ${
                location.pathname === link.path
                  ? "text-white"
                  : "text-[rgba(213,219,230,0.7)] hover:text-white"
              }`}
            >
              {link.label}
            </Link>
          ))}
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
        <div className="md:hidden bg-[rgb(4,7,13)] border-t border-white/5 px-6 py-4 space-y-3">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={`block text-sm py-2 ${
                location.pathname === link.path
                  ? "text-white"
                  : "text-[rgba(213,219,230,0.7)]"
              }`}
            >
              {link.label}
            </Link>
          ))}
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
