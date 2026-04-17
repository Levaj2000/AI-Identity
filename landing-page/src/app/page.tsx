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
  title: "AI Identity — Identity + Context-Aware Policy for Every AI Agent",
  description:
    "Per-agent identity, context-aware policy (ABAC on agent metadata), and cryptographically-signed forensic evidence — DSSE envelopes + ECDSA P-256 signatures that auditors can verify offline. Fail-closed enforcement. Deploy in 15 minutes.",
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
