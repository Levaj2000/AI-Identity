import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import RequestServicesForm from "./request-services-form";

export const metadata: Metadata = generatePageMetadata({
  title: "Request for Services — AI Identity Advisory",
  description:
    "Request an AI Identity advisory engagement: intro call, evidence architecture review, verifiable build advisory, or verifier enablement. Paid engagements with founder Jeff Leva.",
  path: "/request-services",
});

export default function RequestServices() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-12 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Advisory</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Request <span className="text-[rgb(166,218,255)]">services</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[720px] mx-auto leading-relaxed">
            We help you build verifiable systems. Independent auditors verify them. Tell us
            about your situation and we&apos;ll reply with an honest read on whether we can
            help — and what we&apos;d look at first.
          </p>
          <p className="text-sm text-gray-500 max-w-[720px] mx-auto leading-relaxed mt-4">
            All advisory engagements are paid services.
          </p>
        </div>
      </section>

      <div className="max-w-[900px] mx-auto px-6 md:px-12">
        <div className="h-px bg-white/5" />
      </div>

      {/* Form */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <RequestServicesForm />
        </div>
      </section>
    </>
  );
}
