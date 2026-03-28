import BadgeFramerComponent from "../framer/elements/badge";
import MainButtonFramerComponent from "../framer/main-button";
import ProcessFramerComponent from "../framer/process";
import FeatureCard1FramerComponent from "../framer/cards/feature-card-1";
import FeatureCard2FramerComponent from "../framer/cards/feature-card-2";
import FeatureCard3FramerComponent from "../framer/cards/feature-card-3";
import CtaSectionFramerComponent from "../framer/cta-section";
import PricingCardFramerComponent from "../framer/pricing-card";

export default function Home() {
  return (
    <div className="flex flex-col items-center">
      {/* ── Hero Section ── */}
      <section className="relative w-full overflow-hidden pt-32 pb-20 px-6">
        {/* Gradient glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-[radial-gradient(ellipse_at_center,rgba(166,218,255,0.08)_0%,transparent_70%)] pointer-events-none" />

        <div className="relative max-w-[1200px] mx-auto text-center">
          <div className="flex justify-center mb-8">
            <BadgeFramerComponent.Responsive content="IDENTITY FOR AI AGENTS" />
          </div>

          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white leading-[1.1] mb-6 max-w-4xl mx-auto">
            Every AI Agent Deserves an{" "}
            <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
              Identity
            </span>
          </h1>

          <p className="text-lg md:text-xl text-[rgba(213,219,230,0.6)] max-w-2xl mx-auto mb-10">
            Per-agent API keys, scoped permissions, and tamper-proof audit trails.
            Know which agent did what, when, and why -- before regulators ask.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <MainButtonFramerComponent.Responsive
              title="Start Free Trial"
              link="https://dashboard.ai-identity.co"
              newTab={true}
            />
            <a
              href="/how-it-works"
              className="px-6 py-3 rounded-lg border border-[rgba(216,231,242,0.07)] text-sm text-[rgba(213,219,230,0.7)] hover:text-white hover:border-[rgba(216,231,242,0.15)] transition-colors"
            >
              See How It Works
            </a>
          </div>

          {/* Trust badges */}
          <div className="mt-16 flex flex-wrap justify-center gap-8 text-[rgba(213,219,230,0.3)] text-xs uppercase tracking-wider">
            <span>SOC 2 Type II</span>
            <span>EU AI Act Ready</span>
            <span>GDPR Compliant</span>
            <span>ISO 27001</span>
          </div>
        </div>
      </section>

      {/* ── How It Works Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="HOW IT WORKS" />
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
              Three Steps to{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Governed
              </span>{" "}
              AI
            </h2>
            <p className="text-[rgba(213,219,230,0.6)] max-w-xl mx-auto">
              From agent onboarding to continuous compliance -- get up and running in minutes.
            </p>
          </div>

          <div className="flex justify-center">
            <ProcessFramerComponent.Responsive
              step1Heading="Register Agents"
              step1Discription="Issue unique API keys to each AI agent with scoped permissions. Define what each agent can access, which tools it can call, and set rate limits."
              step2Heading="Enforce Policies"
              step2Discription="Apply organization-wide governance rules automatically. Human-in-the-loop approvals, spend limits, and real-time anomaly detection keep agents in check."
              step3Heading="Audit Everything"
              step3Discription="Every agent action is logged with tamper-proof audit trails. Generate compliance reports for SOC 2, EU AI Act, and GDPR with one click."
              imagesVisible={false}
              direction3="Horizontal"
            />
          </div>
        </div>
      </section>

      {/* ── Features Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="CORE CAPABILITIES" />
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
              Built for{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Enterprise
              </span>{" "}
              AI
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FeatureCard1FramerComponent.Responsive
              title="Per-Agent API Keys"
              discription="Issue unique credentials to every AI agent. Rotate, revoke, and scope permissions without downtime."
            />
            <FeatureCard2FramerComponent.Responsive
              title="Real-Time Audit Logs"
              discription="Tamper-proof logs for every agent action. Full chain-of-thought capture for forensic analysis."
            />
            <FeatureCard3FramerComponent.Responsive
              heading="Compliance Dashboard"
              text="SOC 2, EU AI Act, and GDPR compliance monitoring with automated report generation."
            />
          </div>
        </div>
      </section>

      {/* ── Security & Compliance Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="SECURITY" />
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
              Zero-Trust Agent{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Security
              </span>
            </h2>
            <p className="text-[rgba(213,219,230,0.6)] max-w-xl mx-auto">
              Enterprise-grade security designed for autonomous AI systems.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {[
              {
                title: "Scoped Permissions",
                desc: "Fine-grained access control for every agent. Limit tools, APIs, data access, and spending.",
              },
              {
                title: "Anomaly Detection",
                desc: "Real-time behavioral monitoring flags agents acting outside their defined boundaries.",
              },
              {
                title: "Key Rotation",
                desc: "Automatic credential rotation with zero-downtime deployment. Revoke compromised keys instantly.",
              },
              {
                title: "Human-in-the-Loop",
                desc: "Configurable approval gates for high-risk actions. Agents pause and wait for human review.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="p-6 rounded-2xl border border-[rgba(216,231,242,0.07)] bg-[rgb(4,7,13)] hover:border-[rgba(216,231,242,0.15)] transition-colors"
                style={{ boxShadow: "inset 0px 2px 1px 0px rgba(207, 231, 255, 0.1)" }}
              >
                <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-sm text-[rgba(213,219,230,0.6)]">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Forensics Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="FORENSICS" />
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
              AI Agent{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Forensics
              </span>
            </h2>
            <p className="text-[rgba(213,219,230,0.6)] max-w-xl mx-auto">
              When something goes wrong, trace the full chain of events -- from the triggering request to every tool call and decision.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FeatureCard2FramerComponent.Responsive
              title="Chain-of-Thought Logs"
              discription="Capture every reasoning step. Understand why an agent made each decision."
            />
            <FeatureCard1FramerComponent.Responsive
              title="Action Replay"
              discription="Replay agent sessions step-by-step. See exactly what happened, in order."
            />
            <FeatureCard3FramerComponent.Responsive
              heading="Root Cause Analysis"
              text="Automated incident investigation traces failures back to the originating event."
            />
          </div>
        </div>
      </section>

      {/* ── Pricing Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <BadgeFramerComponent.Responsive content="PRICING" />
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
              Simple,{" "}
              <span className="font-['Instrument_Serif'] italic text-[rgb(166,218,255)]">
                Transparent
              </span>{" "}
              Pricing
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <PricingCardFramerComponent.Responsive
              planName="Starter"
              monthlyPrice="$0"
              yearlyPlanMonthlyPrice="$0"
              priceSuffixText="/mo"
              popularTag={false}
              btnText="Get Started"
              btnLink="https://dashboard.ai-identity.co"
              newTab={true}
              point1="5 AI agents"
              point2="Basic audit logs"
              point3="API key management"
              point4="Community support"
              point5="7-day log retention"
              point6=""
              point7=""
            />
            <PricingCardFramerComponent.Responsive
              planName="Pro"
              monthlyPrice="$99"
              yearlyPlanMonthlyPrice="$79"
              priceSuffixText="/mo"
              popularTag={true}
              btnText="Start Free Trial"
              btnLink="https://dashboard.ai-identity.co"
              newTab={true}
              point1="Unlimited agents"
              point2="Advanced audit trails"
              point3="Anomaly detection"
              point4="Compliance reports"
              point5="90-day log retention"
              point6="Priority support"
              point7="Human-in-the-loop"
            />
            <PricingCardFramerComponent.Responsive
              planName="Enterprise"
              monthlyPrice="Custom"
              yearlyPlanMonthlyPrice="Custom"
              priceSuffixText=""
              popularTag={false}
              btnText="Contact Sales"
              btnLink="/contact"
              newTab={false}
              point1="Unlimited everything"
              point2="Custom integrations"
              point3="Dedicated support"
              point4="SLA guarantees"
              point5="Unlimited retention"
              point6="SSO / SAML"
              point7="On-premise option"
            />
          </div>
        </div>
      </section>

      {/* ── CTA Section ── */}
      <section className="w-full py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <CtaSectionFramerComponent.Responsive />
        </div>
      </section>
    </div>
  );
}
