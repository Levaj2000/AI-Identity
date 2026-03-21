import Nav from "./landing/Nav";
import Footer from "./landing/Footer";

export default function CareersPage() {
  return (
    <div className="size-full bg-[#0a0a0b] overflow-auto">
      <Nav />

      <section className="pt-32 pb-24 px-6 md:px-12">
        <div className="max-w-[700px] mx-auto text-center">
          {/* Rocket */}
          <div className="mb-10">
            <div className="w-24 h-24 mx-auto rounded-full bg-[#F59E0B]/10 flex items-center justify-center text-5xl">
              🚀
            </div>
          </div>

          {/* Heading */}
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            We're in{" "}
            <span className="text-[#F59E0B]">Launch Mode</span>
          </h1>

          <p className="text-lg text-gray-400 max-w-[550px] mx-auto mb-8 leading-relaxed">
            Right now, AI Identity is a small team moving fast — building
            the identity infrastructure that will power the autonomous
            agent economy. We're heads down, shipping code, and laying the
            foundation for something big.
          </p>

          {/* Divider */}
          <div className="w-16 h-px bg-[#F59E0B]/30 mx-auto mb-8" />

          <p className="text-base text-gray-300 max-w-[500px] mx-auto mb-12 leading-relaxed">
            As we grow, we'll be looking for engineers, designers, and
            builders who are excited about the intersection of AI, identity,
            and security. If that sounds like you, we'd love to hear from
            you early.
          </p>

          {/* CTA */}
          <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-8 max-w-[480px] mx-auto">
            <h3 className="text-base font-semibold text-white mb-3">
              Want to be first in line?
            </h3>
            <p className="text-sm text-gray-400 mb-6">
              Drop us a note and tell us what you're passionate about.
              We'll reach out when the time is right.
            </p>
            <a
              href="mailto:jeff@ai-identity.co?subject=Career%20Interest%20—%20AI%20Identity"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#F59E0B] text-[#0A0A0B] font-semibold rounded-xl hover:bg-[#F59E0B]/80 transition-colors"
            >
              Say hello
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </a>
          </div>

          {/* Values teaser */}
          <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            <div className="p-6">
              <div className="text-2xl mb-3">⚡</div>
              <h4 className="text-sm font-semibold text-white mb-2">
                Ship Fast
              </h4>
              <p className="text-xs text-gray-500">
                We move quickly, iterate constantly, and put working software
                in front of users.
              </p>
            </div>
            <div className="p-6">
              <div className="text-2xl mb-3">🔐</div>
              <h4 className="text-sm font-semibold text-white mb-2">
                Security First
              </h4>
              <p className="text-xs text-gray-500">
                We're building trust infrastructure. Security isn't a
                feature — it's the foundation.
              </p>
            </div>
            <div className="p-6">
              <div className="text-2xl mb-3">🌍</div>
              <h4 className="text-sm font-semibold text-white mb-2">
                Think Big
              </h4>
              <p className="text-xs text-gray-500">
                We're defining how AI agents operate across the entire
                internet. The opportunity is massive.
              </p>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
