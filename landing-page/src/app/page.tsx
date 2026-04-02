import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import {
  organizationSchema,
  softwareApplicationSchema,
  websiteSchema,
} from "@/lib/schemas";
import JsonLd from "@/components/JsonLd";
import HomeContent from "./home-content";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Identity — Identity Infrastructure for AI Agents",
  description:
    "Per-agent API keys, scoped permissions, and tamper-proof audit trails for autonomous AI agents. SOC 2, EU AI Act, NIST compliant. Deploy in 15 minutes. Free trial.",
  path: "/",
});

export default function HomePage() {
  return (
    <>
      <JsonLd
        data={[organizationSchema, softwareApplicationSchema, websiteSchema]}
      />
      <HomeContent />
    </>
  );
}
