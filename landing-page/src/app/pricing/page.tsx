import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import { softwareApplicationSchema } from "@/lib/schemas";
import JsonLd from "@/components/JsonLd";
import PricingContent from "./pricing-content";

export const metadata: Metadata = generatePageMetadata({
  title: "Pricing — AI Agent Identity & Compliance",
  description:
    "Simple, transparent pricing for AI agent identity infrastructure. Free tier for 5 agents. Pro from $79/mo. Business from $299/mo. Enterprise custom.",
  path: "/pricing",
});

export default function PricingPage() {
  return (
    <>
      <JsonLd data={softwareApplicationSchema} />
      <PricingContent />
    </>
  );
}
