import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";

export const metadata: Metadata = generatePageMetadata({
  title: "Privacy Policy",
  description: "AI Identity privacy policy. How we collect, use, and protect your data.",
  path: "/privacy",
  noIndex: true,
});

const lastUpdated = "March 21, 2026";

const sections = [
  {
    title: "1. Information We Collect",
    content: [
      "We collect information you provide directly when you create an account, register AI agents, or contact us. This includes your name, email address, company name, and billing information.",
      "When you use our API and Gateway services, we collect technical data including API request metadata (timestamps, endpoints called, response codes), agent registration details, and usage metrics. We do not inspect or store the content of communications between AI agents.",
      "We automatically collect standard log data such as IP addresses, browser type, and pages visited when you use our dashboard and website.",
    ],
  },
  {
    title: "2. How We Use Your Information",
    content: [
      "We use your information to provide and maintain the AI Identity platform, process transactions, send service-related communications, and improve our products.",
      "We use usage data to monitor platform health, detect abuse, enforce rate limits, and generate aggregated analytics. We do not sell your personal information to third parties.",
    ],
  },
  {
    title: "3. Data Storage and Security",
    content: [
      "Your data is stored on secure servers hosted in the United States via our infrastructure providers (Neon for databases, Render for API services, Vercel for web applications).",
      "We implement industry-standard security measures including encryption in transit (TLS), encryption at rest, and access controls. API keys and credentials are hashed and never stored in plaintext.",
      "We retain your account data for as long as your account is active. Upon account deletion, we remove your personal data within 30 days, except where retention is required by law.",
    ],
  },
  {
    title: "4. Data Sharing",
    content: [
      "We share data only with service providers necessary to operate the platform: payment processing (Stripe), error monitoring (Sentry), authentication (Clerk), and infrastructure hosting.",
      "We may disclose information if required by law, subpoena, or legal process, or to protect the rights, property, or safety of AI Identity, our users, or the public.",
      "We do not sell, rent, or trade your personal information to third parties for marketing purposes.",
    ],
  },
  {
    title: "5. Cookies and Tracking",
    content: [
      "We use essential cookies to maintain your session and preferences. We use analytics to understand how our website and dashboard are used.",
      "You can control cookie preferences through your browser settings. Disabling essential cookies may affect platform functionality.",
    ],
  },
  {
    title: "6. Your Rights",
    content: [
      "You have the right to access, correct, or delete your personal data. You can export your data or request deletion by contacting us at jeff@ai-identity.co.",
      "If you are a resident of the European Economic Area, you have additional rights under GDPR including the right to data portability and the right to restrict processing.",
      "California residents have additional rights under CCPA including the right to know what personal information is collected and the right to opt out of the sale of personal information.",
    ],
  },
  {
    title: "7. Children's Privacy",
    content: [
      "AI Identity is a B2B service not directed at individuals under 18. We do not knowingly collect personal information from children.",
    ],
  },
  {
    title: "8. Changes to This Policy",
    content: [
      "We may update this Privacy Policy from time to time. We will notify you of material changes by email or through the dashboard. Your continued use of the platform after changes constitutes acceptance of the updated policy.",
    ],
  },
  {
    title: "9. Contact Us",
    content: [
      "For privacy-related questions or requests, contact us at jeff@ai-identity.co or visit our Contact page.",
    ],
  },
];

export default function Privacy() {
  return (
    <section className="pt-32 pb-24 px-6 md:px-12">
      <div className="max-w-[800px] mx-auto">
        <div className="mb-16 text-center">
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-4">
            Privacy <span className="text-[rgb(166,218,255)]">Policy</span>
          </h1>
          <p className="text-gray-400 text-sm">Last updated: {lastUpdated}</p>
        </div>

        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-8 mb-12">
          <p className="text-sm text-gray-300 leading-relaxed">
            AI Identity LLC (&ldquo;AI Identity&rdquo;, &ldquo;we&rdquo;, &ldquo;our&rdquo;, or &ldquo;us&rdquo;) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform, API, and website at ai-identity.co.
          </p>
        </div>

        <div className="space-y-10">
          {sections.map((section, i) => (
            <div key={i}>
              <h2 className="text-lg font-bold text-white mb-4">{section.title}</h2>
              <div className="space-y-3">
                {section.content.map((paragraph, j) => (
                  <p key={j} className="text-sm text-gray-400 leading-relaxed">{paragraph}</p>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-16 pt-8 border-t border-white/10 text-center">
          <p className="text-sm text-gray-500">AI Identity LLC &middot; Colorado, United States</p>
          <a href="mailto:jeff@ai-identity.co?subject=Privacy%20Inquiry" className="text-sm text-[rgb(166,218,255)] hover:underline">
            jeff@ai-identity.co
          </a>
        </div>
      </div>
    </section>
  );
}
