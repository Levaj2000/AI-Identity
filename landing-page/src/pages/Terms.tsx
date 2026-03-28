const lastUpdated = "March 21, 2026";

const sections = [
  {
    title: "1. Acceptance of Terms",
    content: [
      'By accessing or using the AI Identity platform, API, dashboard, or website (collectively, the "Service"), you agree to be bound by these Terms of Service. If you are using the Service on behalf of an organization, you represent that you have authority to bind that organization to these terms.',
      "If you do not agree to these terms, do not use the Service.",
    ],
  },
  {
    title: "2. Description of Service",
    content: [
      "AI Identity provides identity verification, authentication, and access control infrastructure for AI agents. The Service includes the AI Identity API, Gateway, Dashboard, and related documentation.",
      "We may update, modify, or discontinue features of the Service at any time. We will provide reasonable notice of material changes.",
    ],
  },
  {
    title: "3. Account Registration",
    content: [
      "You must create an account to use the Service. You are responsible for maintaining the confidentiality of your account credentials and for all activities under your account.",
      "You agree to provide accurate and complete registration information and to update it as needed. You must notify us immediately of any unauthorized use of your account.",
    ],
  },
  {
    title: "4. Acceptable Use",
    content: [
      "You agree to use the Service only for lawful purposes and in accordance with these terms. You will not use the Service to facilitate illegal activity, violate third-party rights, or distribute malware.",
      "You will not attempt to reverse engineer, decompile, or disassemble the Service, or circumvent any access controls, rate limits, or security measures.",
      "You are responsible for ensuring that AI agents registered through your account comply with applicable laws and regulations.",
    ],
  },
  {
    title: "5. API Usage and Rate Limits",
    content: [
      "Your use of the API is subject to the rate limits and usage quotas associated with your subscription plan. Exceeding these limits may result in throttling or temporary suspension of access.",
      "API keys are confidential and must not be shared publicly or embedded in client-side code. You are responsible for securing your API keys and rotating them if compromised.",
    ],
  },
  {
    title: "6. Payment and Billing",
    content: [
      "Paid plans are billed in advance on a monthly or annual basis. All fees are non-refundable except as required by law or as explicitly stated in your plan terms.",
      "We may change pricing with 30 days' notice. Price changes will take effect at the start of your next billing cycle. You may cancel your subscription at any time; cancellation takes effect at the end of the current billing period.",
      "Payment processing is handled by Stripe. By providing payment information, you agree to Stripe's terms of service.",
    ],
  },
  {
    title: "7. Data Ownership",
    content: [
      "You retain ownership of all data you provide to the Service, including agent configurations, API request metadata, and account information.",
      "You grant AI Identity a limited license to use your data solely to provide and improve the Service. We will not use your data for purposes unrelated to the Service without your consent.",
      "AI Identity owns all intellectual property in the Service itself, including the platform, API, documentation, and branding.",
    ],
  },
  {
    title: "8. Service Level and Support",
    content: [
      "We strive to maintain high availability of the Service but do not guarantee uninterrupted access. Scheduled maintenance windows will be communicated in advance when possible.",
      "Support is provided via email at jeff@ai-identity.co. Response times vary by plan and issue severity. Critical issues affecting production systems are prioritized.",
    ],
  },
  {
    title: "9. Limitation of Liability",
    content: [
      'THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. AI IDENTITY DOES NOT WARRANT THAT THE SERVICE WILL BE UNINTERRUPTED, ERROR-FREE, OR SECURE.',
      "TO THE MAXIMUM EXTENT PERMITTED BY LAW, AI IDENTITY'S TOTAL LIABILITY FOR ANY CLAIMS ARISING FROM YOUR USE OF THE SERVICE IS LIMITED TO THE AMOUNTS YOU PAID TO AI IDENTITY IN THE 12 MONTHS PRECEDING THE CLAIM.",
      "AI IDENTITY IS NOT LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOSS OF PROFITS, DATA, OR BUSINESS OPPORTUNITIES.",
    ],
  },
  {
    title: "10. Indemnification",
    content: [
      "You agree to indemnify and hold harmless AI Identity, its officers, directors, and employees from any claims, damages, or expenses arising from your use of the Service, your violation of these terms, or your violation of any third-party rights.",
    ],
  },
  {
    title: "11. Termination",
    content: [
      "Either party may terminate this agreement at any time. You may cancel your account through the dashboard or by contacting us.",
      "We may suspend or terminate your access if you violate these terms, fail to pay fees, or if we reasonably believe your use poses a risk to the Service or other users.",
      "Upon termination, your right to use the Service ceases immediately. You may request export of your data within 30 days of termination.",
    ],
  },
  {
    title: "12. Governing Law",
    content: [
      "These terms are governed by the laws of the State of Colorado, United States, without regard to conflict of law principles. Any disputes will be resolved in the courts of Colorado.",
    ],
  },
  {
    title: "13. Changes to Terms",
    content: [
      "We may update these Terms of Service from time to time. We will notify you of material changes by email or through the dashboard at least 30 days before they take effect.",
      "Your continued use of the Service after changes take effect constitutes acceptance of the updated terms.",
    ],
  },
  {
    title: "14. Contact",
    content: [
      "For questions about these Terms of Service, contact us at jeff@ai-identity.co or visit our Contact page.",
    ],
  },
];

export default function Terms() {
  return (
    <section className="pt-32 pb-24 px-6 md:px-12">
      <div className="max-w-[800px] mx-auto">
        {/* Header */}
        <div className="mb-16 text-center">
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-4">
            Terms of <span className="text-[rgb(166,218,255)]">Service</span>
          </h1>
          <p className="text-gray-400 text-sm">
            Last updated: {lastUpdated}
          </p>
        </div>

        {/* Intro */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-8 mb-12">
          <p className="text-sm text-gray-300 leading-relaxed">
            These Terms of Service ("Terms") govern your use of the AI
            Identity platform and services operated by AI Identity LLC, a
            Colorado limited liability company. Please read these terms
            carefully before using our services.
          </p>
        </div>

        {/* Sections */}
        <div className="space-y-10">
          {sections.map((section, i) => (
            <div key={i}>
              <h2 className="text-lg font-bold text-white mb-4">
                {section.title}
              </h2>
              <div className="space-y-3">
                {section.content.map((paragraph, j) => (
                  <p key={j} className="text-sm text-gray-400 leading-relaxed">
                    {paragraph}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer note */}
        <div className="mt-16 pt-8 border-t border-white/10 text-center">
          <p className="text-sm text-gray-500">
            AI Identity LLC &middot; Colorado, United States
          </p>
          <a
            href="mailto:jeff@ai-identity.co?subject=Terms%20Inquiry"
            className="text-sm text-[rgb(166,218,255)] hover:underline"
          >
            jeff@ai-identity.co
          </a>
        </div>
      </div>
    </section>
  );
}
