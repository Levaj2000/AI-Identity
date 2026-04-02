import { useState } from "react";
import SEO from "../components/SEO";

const faqs = [
  {
    q: "What is AI Identity?",
    a: "AI Identity is an infrastructure platform that provides identity, authentication, and access control for AI agents. We help enterprises register, govern, and monitor autonomous agents operating across organizational boundaries.",
  },
  {
    q: "How do I get started?",
    a: "Sign up for a free account on our dashboard, register your first agent, and integrate using our API. Most teams are up and running in under 15 minutes.",
  },
  {
    q: "What does pricing look like?",
    a: "We offer a free tier for small teams and startups. Pro and Enterprise plans scale based on the number of registered agents and API calls. Visit our Pricing page for full details.",
  },
  {
    q: "How do I report a bug or issue?",
    a: "Use the contact form on this page with the subject set to 'Bug Report', or email us directly at jeff@ai-identity.co. Include steps to reproduce the issue and any error messages you see.",
  },
  {
    q: "What kind of support do you offer?",
    a: "All plans include email support. We respond to general inquiries within 24 hours and critical issues within 4 hours during business hours (Mon-Fri, 9am-6pm MT).",
  },
];

export default function Contact() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("General Inquiry");
  const [message, setMessage] = useState("");
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const mailtoSubject = encodeURIComponent(`[${subject}] from ${name}`);
    const mailtoBody = encodeURIComponent(
      `Name: ${name}\nEmail: ${email}\nSubject: ${subject}\n\n${message}`
    );
    window.location.href = `mailto:jeff@ai-identity.co?subject=${mailtoSubject}&body=${mailtoBody}`;
    setSubmitted(true);
  };

  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
      <SEO
        title="Contact AI Identity"
        description="Get in touch with the AI Identity team. Schedule a demo, ask a question, or explore design partnership opportunities."
        path="/contact"
      />
        <div className="max-w-[800px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">
              We'd love to hear from you
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Get in <span className="text-[rgb(166,218,255)]">Touch</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[600px] mx-auto">
            Have a question, need support, or interested in a partnership?
            Reach out and we'll get back to you within 24 hours.
          </p>
        </div>
      </section>

      {/* Contact Form + Info */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[1000px] mx-auto grid grid-cols-1 lg:grid-cols-5 gap-12">
          {/* Form */}
          <div className="lg:col-span-3">
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-8">
              {submitted ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-[rgb(166,218,255)]/10 flex items-center justify-center">
                    <svg
                      width="32"
                      height="32"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="rgb(166,218,255)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">
                    Message ready to send!
                  </h3>
                  <p className="text-gray-400 mb-6">
                    Your email client should have opened with your message. If
                    not, email us directly at{" "}
                    <a
                      href="mailto:jeff@ai-identity.co"
                      className="text-[rgb(166,218,255)] hover:underline"
                    >
                      jeff@ai-identity.co
                    </a>
                  </p>
                  <button
                    onClick={() => {
                      setSubmitted(false);
                      setName("");
                      setEmail("");
                      setSubject("General Inquiry");
                      setMessage("");
                    }}
                    className="text-sm text-[rgb(166,218,255)] hover:underline"
                  >
                    Send another message
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Name
                      </label>
                      <input
                        type="text"
                        required
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Your name"
                        className="w-full px-4 py-3 bg-[rgb(16,19,28)] border border-white/10 rounded-xl text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-[rgb(166,218,255)]/40 transition-colors"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Email
                      </label>
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@company.com"
                        className="w-full px-4 py-3 bg-[rgb(16,19,28)] border border-white/10 rounded-xl text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-[rgb(166,218,255)]/40 transition-colors"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Subject
                    </label>
                    <select
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      className="w-full px-4 py-3 bg-[rgb(16,19,28)] border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-[rgb(166,218,255)]/40 transition-colors appearance-none cursor-pointer"
                    >
                      <option value="General Inquiry">General Inquiry</option>
                      <option value="Support">Support</option>
                      <option value="Sales & Partnerships">
                        Sales & Partnerships
                      </option>
                      <option value="Bug Report">Bug Report</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Message
                    </label>
                    <textarea
                      required
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      placeholder="Tell us how we can help..."
                      rows={5}
                      className="w-full px-4 py-3 bg-[rgb(16,19,28)] border border-white/10 rounded-xl text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-[rgb(166,218,255)]/40 transition-colors resize-none"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors"
                  >
                    Send Message
                  </button>
                </form>
              )}
            </div>
          </div>

          {/* Info sidebar */}
          <div className="lg:col-span-2 space-y-8">
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="4" width="20" height="16" rx="2" />
                    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                  </svg>
                </div>
                <h3 className="text-base font-semibold text-white">Email</h3>
              </div>
              <a href="mailto:jeff@ai-identity.co" className="text-[rgb(166,218,255)] text-sm hover:underline">
                jeff@ai-identity.co
              </a>
            </div>

            <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgb(166,218,255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                </div>
                <h3 className="text-base font-semibold text-white">Response Time</h3>
              </div>
              <p className="text-sm text-gray-400">General inquiries: within 24 hours</p>
              <p className="text-sm text-gray-400">Critical issues: within 4 hours</p>
              <p className="text-xs text-gray-500 mt-2">Mon-Fri, 9am-6pm Mountain Time</p>
            </div>

            <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-6">
              <h3 className="text-base font-semibold text-white mb-2">Become a Design Partner</h3>
              <p className="text-sm text-gray-400 mb-4">
                Get free early access, shape the product roadmap, and lock in preferred pricing.
              </p>
              <a
                href="mailto:jeff@ai-identity.co?subject=Design%20Partner%20Interest"
                className="inline-flex items-center gap-2 text-sm text-[rgb(166,218,255)] font-medium hover:underline"
              >
                Get in touch
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white text-center mb-12">
            Frequently Asked Questions
          </h2>
          <div className="space-y-3">
            {faqs.map((faq, i) => (
              <div key={i} className="bg-white/[0.03] border border-white/10 rounded-xl overflow-hidden">
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between p-5 text-left"
                >
                  <span className="text-sm font-medium text-white pr-4">{faq.q}</span>
                  <svg
                    width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    className={`shrink-0 transition-transform ${openFaq === i ? "rotate-180" : ""}`}
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
                {openFaq === i && (
                  <div className="px-5 pb-5">
                    <p className="text-sm text-gray-400 leading-relaxed">{faq.a}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
