import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { generatePageMetadata } from "@/lib/metadata";

export const metadata: Metadata = generatePageMetadata({
  title: "About AI Identity — Mission, Founder & Values",
  description:
    "AI Identity was created to help organizations use AI in ways that are responsible, auditable, and genuinely useful to people. Meet the founder and learn what drives us.",
  path: "/about",
});

export default function About() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">About</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            About <span className="text-[rgb(166,218,255)]">AI Identity</span>
          </h1>
        </div>
      </section>

      {/* About AI Identity */}
      <section className="pb-16 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto space-y-5">
          <p className="text-base text-gray-300 leading-relaxed">
            AI Identity was created to solve a technical problem, but not only a technical problem.
          </p>
          <p className="text-sm text-gray-400 leading-relaxed">
            As AI agents become more autonomous, businesses need better ways to know which agent did what, enforce clear boundaries, and reconstruct incidents when something goes wrong. Shared API keys and opaque logs make that almost impossible. AI Identity gives every agent its own identity at the API layer so teams can deploy AI agents with accountability built in.
          </p>
          <p className="text-sm text-gray-400 leading-relaxed">
            Behind that, there is a deeper motivation: helping organizations use AI in ways that are responsible, auditable, and genuinely useful to people. The goal is not just to ship infrastructure, but to help teams build systems they can trust — and that their customers can trust — over the long term.
          </p>
        </div>
      </section>

      <div className="max-w-[800px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* From the Founder */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="flex flex-col md:flex-row gap-10 items-start">
            {/* Photo */}
            <div className="flex-shrink-0 mx-auto md:mx-0">
              <div className="w-64 h-72 rounded-2xl overflow-hidden border border-white/10">
                <Image
                  src="/images/jeff-leva.jpg"
                  alt="Jeff Leva, Founder of AI Identity"
                  width={256}
                  height={288}
                  className="w-full h-full object-cover"
                  priority
                />
              </div>
              <div className="mt-3 text-center md:text-left">
                <p className="text-base font-semibold text-white">Jeff Leva</p>
                <p className="text-xs text-gray-500">Founder &amp; CEO</p>
              </div>
            </div>

            {/* Story */}
            <div className="space-y-5">
              <h2 className="text-2xl md:text-3xl font-bold text-white">From the Founder</h2>
              <p className="text-sm text-gray-400 leading-relaxed">
                I&apos;m Jeff Leva, the founder of AI Identity.
              </p>
              <p className="text-sm text-gray-400 leading-relaxed">
                I&apos;ve spent my career close to production systems and the people who have to keep them safe and running. When I started working with AI agents in real environments, I kept running into the same pattern: powerful tools running with shared credentials, minimal guardrails, and no clean way to answer who did what when something broke.
              </p>
              <p className="text-sm text-gray-400 leading-relaxed">
                AI Identity grew out of that experience. I wanted a way for teams to give each agent its own cryptographic key, clearly scoped permissions, and a tamper-proof record of every action — without a six-month project or enterprise-only tooling.
              </p>
              <p className="text-sm text-gray-400 leading-relaxed">
                More importantly, I wanted the company to be built around service, not just software. That means being clear about what we do, honest about what we don&apos;t, and designing the product to help teams meet real obligations to their customers, regulators, and stakeholders.
              </p>
            </div>
          </div>
        </div>
      </section>

      <div className="max-w-[800px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* What We Believe */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-6">What We Believe</h2>
          <p className="text-sm text-gray-400 leading-relaxed mb-6">
            AI Identity is built on a few simple principles.
          </p>

          <div className="space-y-4 mb-8">
            {[
              "Every AI agent should have a real, verifiable identity — not a shared key and a best guess.",
              "Permissions should be explicit and least-privilege by default, with systems that fail closed when there\u2019s uncertainty.",
              "Audit trails should be tamper-evident and useful for real investigations, not just another log table.",
            ].map((principle, i) => (
              <div key={i} className="flex items-start gap-3 bg-white/[0.03] border border-white/10 rounded-xl p-5">
                <svg className="w-5 h-5 text-[rgb(166,218,255)] flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <p className="text-sm text-gray-300 leading-relaxed">{principle}</p>
              </div>
            ))}
          </div>

          <p className="text-sm text-gray-400 leading-relaxed">
            We also believe that security and compliance should serve people, not just check boxes. The right infrastructure should make it easier for teams to do the right thing by default — to prevent harm, respond quickly when issues occur, and show their work when someone asks how a system made a decision.
          </p>
        </div>
      </section>

      <div className="max-w-[800px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* Technology in the Service of Others */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-6">Technology in the Service of Others</h2>
          <div className="space-y-5">
            <p className="text-sm text-gray-400 leading-relaxed">
              AI Identity exists to help businesses and teams serve others better through technology.
            </p>
            <p className="text-sm text-gray-400 leading-relaxed">
              That starts with the product: giving teams the tools they need to run AI agents with clarity, safety, and accountability. But it shouldn&apos;t stop at the product boundary. As the company grows, we want the business itself to be a small force for good.
            </p>
            <p className="text-sm text-gray-400 leading-relaxed">
              To reflect that, a portion of AI Identity&apos;s business sales will be directed to organizations working with people and communities in need. As revenue grows, we&apos;ll share more concretely how that support is allocated and which organizations we&apos;re partnering with, so customers can see the impact their spend helps enable.
            </p>
          </div>
        </div>
      </section>

      <div className="max-w-[800px] mx-auto px-6 md:px-12"><div className="h-px bg-white/5" /></div>

      {/* How AI Identity Helps Today */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-6">How AI Identity Helps Today</h2>
          <div className="space-y-5 mb-10">
            <p className="text-sm text-gray-400 leading-relaxed">
              Practically, AI Identity gives teams three things: per-agent API keys with scoped permissions, a gateway that enforces policy at the point of use, and hash-chained audit logs that make every agent action traceable and tamper-evident.
            </p>
            <p className="text-sm text-gray-400 leading-relaxed">
              That combination helps organizations answer the hard questions — who called which model, under what authorization, and what happened next — and gives them a foundation for meeting frameworks like the EU AI Act, SOC 2, NIST AI RMF, and similar standards.
            </p>
            <p className="text-sm text-gray-400 leading-relaxed">
              If you&apos;re running AI agents today and want stronger identity and accountability — or if you&apos;re just thinking through what responsible deployment should look like for your team — I&apos;d be glad to hear from you.
            </p>
          </div>

          {/* CTA */}
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h3 className="text-xl font-bold text-white mb-3">Let&apos;s talk</h3>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Whether you&apos;re exploring agent governance or ready to deploy, we&apos;d love to hear from you.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <a href="https://dashboard.ai-identity.co" className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
                Get Started Free
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </a>
              <Link href="/contact" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                Contact Jeff
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
