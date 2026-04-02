"use client";

import Link from "next/link";
import { useState } from "react";

const productLinks = [
  { label: "How It Works", path: "/how-it-works" },
  { label: "Security", path: "/security" },
  { label: "Integrations", path: "/integrations" },
  { label: "Pricing", path: "/contact" },
  { label: "Architecture", path: "/architecture" },
  { label: "Documentation", path: "/docs" },
  { label: "EU AI Act Checklist", path: "/eu-ai-act-checklist" },
  { label: "Dashboard", path: "https://dashboard.ai-identity.co", external: true },
];

const solutionLinks = [
  { label: "Customer Support Agents", path: "/use-cases/customer-support" },
  { label: "Coding Assistants", path: "/use-cases/coding-assistant" },
  { label: "Financial Compliance", path: "/use-cases/financial-compliance" },
];

const companyLinks = [
  { label: "Blog", path: "/blog" },
  { label: "Careers", path: "/careers" },
  { label: "Contact", path: "/contact" },
  { label: "Terms", path: "/terms" },
];

export default function Footer() {
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubscribe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    try {
      await fetch("https://buttondown.com/api/emails/embed-subscribe/ai-identity", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `email=${encodeURIComponent(email)}`,
        mode: "no-cors",
      });
      setSubscribed(true);
      setEmail("");
    } catch {
      // no-cors always appears to succeed
      setSubscribed(true);
      setEmail("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <footer className="border-t border-[rgba(216,231,242,0.07)] bg-[rgb(4,7,13)]">
      <div className="max-w-[1200px] mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12">
          {/* Brand + Newsletter */}
          <div className="md:col-span-2">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 flex items-center justify-center">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
                  <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                  <path d="M2 17l10 5 10-5"/>
                  <path d="M2 12l10 5 10-5"/>
                </svg>
              </div>
              <span className="text-white font-semibold text-lg">AI Identity</span>
            </Link>
            <p className="text-sm text-[rgba(213,219,230,0.5)] mb-6 max-w-sm">
              Identity infrastructure for AI agents. Per-agent API keys, scoped permissions, and tamper-proof audit trails.
            </p>

            {/* Newsletter */}
            {subscribed ? (
              <p className="text-sm text-[rgb(166,218,255)]">Thanks for subscribing!</p>
            ) : (
              <form onSubmit={handleSubscribe} className="flex gap-2 max-w-sm">
                <label htmlFor="newsletter-email" className="sr-only">Email address for newsletter</label>
                <input
                  id="newsletter-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  aria-label="Email address for newsletter"
                  className="flex-1 px-4 py-2 rounded-lg bg-[rgb(16,19,28)] border border-[rgba(216,231,242,0.07)] text-sm text-white placeholder-[rgba(213,219,230,0.55)] focus:outline-none focus:border-[rgb(166,218,255)]/30"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 rounded-lg bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 text-[rgb(166,218,255)] text-sm font-medium hover:bg-[rgb(166,218,255)]/20 transition-colors disabled:opacity-50"
                >
                  {loading ? "..." : "Subscribe"}
                </button>
              </form>
            )}

            {/* Social */}
            <div className="flex gap-4 mt-6">
              {[
                { label: "X", href: "https://x.com/ai_identity_co", icon: "M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" },
                { label: "LinkedIn", href: "https://linkedin.com/company/ai-identity", icon: "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" },
                { label: "GitHub", href: "https://github.com/ai-identity", icon: "M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" },
              ].map((social) => (
                <a key={social.label} href={social.href} target="_blank" rel="noopener noreferrer" className="text-[rgba(213,219,230,0.5)] hover:text-white transition-colors" aria-label={social.label}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d={social.icon} /></svg>
                </a>
              ))}
            </div>
          </div>

          {/* Product Links */}
          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Product</h4>
            <ul className="space-y-3">
              {productLinks.map((link) => (
                <li key={link.label}>
                  {"external" in link ? (
                    <a href={link.path} target="_blank" rel="noopener noreferrer" className="text-sm text-[rgba(213,219,230,0.5)] hover:text-white transition-colors">{link.label}</a>
                  ) : (
                    <Link href={link.path} className="text-sm text-[rgba(213,219,230,0.5)] hover:text-white transition-colors">{link.label}</Link>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {/* Solutions Links */}
          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Solutions</h4>
            <ul className="space-y-3">
              {solutionLinks.map((link) => (
                <li key={link.label}>
                  <Link href={link.path} className="text-sm text-[rgba(213,219,230,0.5)] hover:text-white transition-colors">{link.label}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company Links */}
          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Company</h4>
            <ul className="space-y-3">
              {companyLinks.map((link) => (
                <li key={link.label}>
                  <Link href={link.path} className="text-sm text-[rgba(213,219,230,0.5)] hover:text-white transition-colors">{link.label}</Link>
                </li>
              ))}
            </ul>
            <div className="mt-6">
              <a href="mailto:jeff@ai-identity.co" className="text-sm text-[rgba(213,219,230,0.5)] hover:text-white transition-colors">jeff@ai-identity.co</a>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-16 pt-8 border-t border-[rgba(216,231,242,0.07)] flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-[rgba(213,219,230,0.55)]">&copy; {new Date().getFullYear()} AI Identity. All rights reserved.</p>
          <div className="flex gap-6">
            <Link href="/privacy" className="text-xs text-[rgba(213,219,230,0.55)] hover:text-white transition-colors">Privacy</Link>
            <Link href="/terms" className="text-xs text-[rgba(213,219,230,0.55)] hover:text-white transition-colors">Terms</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
