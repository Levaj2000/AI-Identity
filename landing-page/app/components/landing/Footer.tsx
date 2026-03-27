import { useState } from "react";

const BUTTONDOWN_URL =
  "https://buttondown.com/api/emails/embed-subscribe/ai-identity";

const productLinks = [
  { label: "How It Works", href: "/how-it-works" },
  { label: "Integrations", href: "/integrations" },
  { label: "Security", href: "/security" },
  { label: "Pricing", href: "/contact" },
  { label: "Architecture", href: "/architecture" },
  { label: "Dashboard", href: "https://dashboard.ai-identity.co" },
  { label: "Documentation", href: "/docs" },
  { label: "EU AI Act Checklist", href: "/eu-ai-act-checklist" },
];

const companyLinks = [
  { label: "Blog", href: "/blog" },
  { label: "Careers", href: "/careers" },
  { label: "Contact", href: "/contact" },
  { label: "Legal", href: "/terms" },
];

function SocialIcon({
  d,
  label,
  href,
}: {
  d: string;
  label: string;
  href: string;
}) {
  return (
    <a
      href={href}
      aria-label={label}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[#F59E0B]/60 hover:text-[#F59E0B] transition-colors"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
        <path d={d} />
      </svg>
    </a>
  );
}

export default function Footer() {
  const [email, setEmail] = useState("");
  const [subscribeStatus, setSubscribeStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");

  const handleSubscribe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setSubscribeStatus("loading");
    try {
      const res = await fetch(BUTTONDOWN_URL, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ email }),
      });
      if (res.ok || res.status === 201) {
        setSubscribeStatus("success");
        setEmail("");
      } else {
        setSubscribeStatus("error");
      }
    } catch {
      setSubscribeStatus("error");
    }
  };

  return (
    <footer className="bg-[#0F1724] border-t border-white/5">
      <div className="max-w-[1200px] mx-auto px-6 md:px-12 py-20">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-16">
          {/* Brand + Subscribe */}
          <div className="lg:col-span-1">
            <div className="flex items-center gap-2.5 mb-6">
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
              <span className="text-base font-semibold text-[#F59E0B]">
                AI Identity
              </span>
            </div>
            <p className="text-sm text-[#8B9BB4] mb-6 leading-relaxed">
              Get updates on new features and product releases.
            </p>
            {subscribeStatus === "success" ? (
              <p className="text-sm text-[#F59E0B] font-medium">
                ✓ Subscribed! Check your email to confirm.
              </p>
            ) : (
              <form
                onSubmit={handleSubscribe}
                className="flex gap-2 max-w-[260px]"
              >
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@email.com"
                  required
                  className="min-w-0 flex-1 px-3 py-2 bg-[#131E30] border border-white/10 rounded-lg text-xs text-white placeholder:text-[#4A5B73] focus:outline-none focus:border-[#F59E0B]/40"
                />
                <button
                  type="submit"
                  disabled={subscribeStatus === "loading"}
                  className="px-3 py-2 bg-[#F59E0B] text-[#0F1724] text-xs font-semibold rounded-lg hover:bg-[#F59E0B]/80 transition-colors shrink-0 disabled:opacity-50"
                >
                  {subscribeStatus === "loading" ? "..." : "Subscribe"}
                </button>
              </form>
            )}
            {subscribeStatus === "error" && (
              <p className="text-xs text-red-400 mt-2">
                Something went wrong. Try again or email us directly.
              </p>
            )}
          </div>

          {/* Product */}
          <div>
            <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-5">
              Product
            </h4>
            <ul className="space-y-3">
              {productLinks.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-sm text-[#8B9BB4] hover:text-white transition-colors"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-5">
              Company
            </h4>
            <ul className="space-y-3">
              {companyLinks.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-sm text-[#8B9BB4] hover:text-white transition-colors"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Social */}
          <div>
            <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-5">
              Connect
            </h4>
            <div className="flex gap-5">
              {/* X (Twitter) */}
              <SocialIcon
                label="X (Twitter)"
                href="https://x.com/AIIdentity"
                d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"
              />
              {/* LinkedIn */}
              <SocialIcon
                label="LinkedIn"
                href="https://www.linkedin.com/company/ai-identity"
                d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
              />
              {/* GitHub */}
              <SocialIcon
                label="GitHub"
                href="https://github.com/Levaj2000/AI-Identity"
                d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
              />
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-20 pt-8 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-[#6B7C96]">
            &copy; 2026 AI Identity. All rights reserved.
          </p>
          <div className="flex items-center gap-6 text-sm text-[#6B7C96]">
            <a href="/privacy" className="hover:text-[#8B9BB4] transition-colors">
              Privacy Policy
            </a>
            <a href="/terms" className="hover:text-[#8B9BB4] transition-colors">
              Terms of Service
            </a>
            <button className="hover:text-[#8B9BB4] transition-colors">
              Cookie Settings
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
}
