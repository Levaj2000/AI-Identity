import { useState, useEffect } from "react";

const navLinks = [
  { label: "Home", href: "/", sectionId: "" },
  { label: "How It Works", href: "/how-it-works", sectionId: "how-it-works" },
  { label: "Compliance", href: "/security", sectionId: "compliance" },
  { label: "Forensics", href: "/security", sectionId: "forensics" },
  { label: "Security", href: "/security", sectionId: "security" },
  { label: "Integrations", href: "/integrations", sectionId: "integrations" },
  { label: "Pricing", href: "/contact", sectionId: "pricing" },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("");

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 20);

      // Determine which section is currently in view
      const sections = navLinks
        .filter((l) => l.sectionId)
        .map((l) => ({
          id: l.sectionId,
          el: document.getElementById(l.sectionId),
        }))
        .filter((s) => s.el);

      // If near top of page, highlight Home
      if (window.scrollY < 300) {
        setActiveSection("");
        return;
      }

      // Find the section whose top is closest to (but above) the viewport center
      const viewportCenter = window.scrollY + window.innerHeight / 3;
      let current = "";
      for (const section of sections) {
        if (section.el && section.el.offsetTop <= viewportCenter) {
          current = section.id;
        }
      }
      setActiveSection(current);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll(); // run once on mount
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleClick = (
    e: React.MouseEvent<HTMLAnchorElement>,
    sectionId: string,
  ) => {
    const isHome = window.location.pathname === "/";

    if (!sectionId) {
      e.preventDefault();
      if (isHome) {
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        window.location.href = "/";
      }
      setMobileOpen(false);
      return;
    }
    const el = document.getElementById(sectionId);
    if (el) {
      e.preventDefault();
      el.scrollIntoView({ behavior: "smooth" });
      setMobileOpen(false);
    }
    // If section not found on page, let the browser navigate to the href
  };

  const isActive = (sectionId: string) => {
    if (sectionId === "" && activeSection === "") return true;
    return sectionId === activeSection;
  };

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#0A0A0B]/80 backdrop-blur-xl border-b border-white/5"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-[1400px] mx-auto px-6 md:px-10 h-[72px] flex items-center justify-between">
        {/* Logo */}
        <a
          href="#"
          onClick={(e) => handleClick(e, "")}
          className="flex items-center gap-2"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            className="text-[#F59E0B]"
          >
            <rect
              x="3"
              y="12"
              width="4"
              height="8"
              rx="1"
              fill="currentColor"
              opacity="0.6"
            />
            <rect
              x="10"
              y="8"
              width="4"
              height="12"
              rx="1"
              fill="currentColor"
              opacity="0.8"
            />
            <rect
              x="17"
              y="4"
              width="4"
              height="16"
              rx="1"
              fill="currentColor"
            />
          </svg>
          <span className="text-lg font-semibold text-[#F59E0B]">
            AI Identity
          </span>
        </a>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-6 lg:gap-8">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={(e) => handleClick(e, link.sectionId)}
              className={`text-sm transition-colors relative ${
                isActive(link.sectionId)
                  ? "text-[#F59E0B] font-medium"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {link.label}
              {isActive(link.sectionId) && (
                <span className="absolute -bottom-1 left-0 right-0 h-[2px] bg-[#F59E0B] rounded-full" />
              )}
            </a>
          ))}
        </div>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-5 lg:gap-6">
          <a
            href="https://dashboard.ai-identity.co/demo"
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Live Demo
          </a>
          <a
            href="/docs"
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Docs
          </a>
          <a
            href="/blog"
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Blog
          </a>
          <a
            href="https://dashboard.ai-identity.co"
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Dashboard
          </a>
          <a
            href="/contact"
            onClick={(e) => handleClick(e, "pricing")}
            className="px-5 py-2 bg-[#F59E0B] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#F59E0B]/80 transition-colors"
          >
            Get Started
          </a>
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden text-gray-400"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            {mobileOpen ? (
              <path d="M6 6l12 12M6 18L18 6" />
            ) : (
              <path d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-[#0A0A0B]/95 backdrop-blur-xl border-t border-white/5 px-6 pb-6">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={(e) => handleClick(e, link.sectionId)}
              className={`block py-3 text-sm transition-colors ${
                isActive(link.sectionId)
                  ? "text-[#F59E0B] font-medium"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {link.label}
            </a>
          ))}
          <a
            href="https://dashboard.ai-identity.co/demo"
            className="block py-3 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Live Demo
          </a>
          <a
            href="/docs"
            className="block py-3 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Docs
          </a>
          <a
            href="/blog"
            className="block py-3 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Blog
          </a>
          <a
            href="https://dashboard.ai-identity.co"
            className="block py-3 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Dashboard
          </a>
          <a
            href="/contact"
            onClick={(e) => handleClick(e, "pricing")}
            className="mt-3 block text-center px-5 py-2 bg-[#F59E0B] text-[#0A0A0B] text-sm font-semibold rounded-lg"
          >
            Get Started
          </a>
        </div>
      )}
    </nav>
  );
}
