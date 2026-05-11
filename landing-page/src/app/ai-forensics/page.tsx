import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import AIForensicsContent from "./ai-forensics-content";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Forensics — Replay-Grade Evidence for AI Agent Incidents",
  description: "Tamper-evident, chain-of-thought audit trails for AI agent decisions. Replay any agent session step-by-step a year later — incident response, regulator reviews, internal audits.",
  path: "/ai-forensics",
});

export default function AIForensicsPage() {
  return <AIForensicsContent />;
}
