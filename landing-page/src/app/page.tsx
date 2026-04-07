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
  title: "AI Identity — Forensic-Grade Accountability for Every AI Agent",
  description:
    "Replay any agent session step-by-step. Produce tamper-evident timelines regulators can verify independently. Per-agent identity, fail-closed enforcement, and HMAC-SHA256 forensic audit trails. Deploy in 15 minutes.",
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
