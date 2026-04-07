import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import RoiCalculator from "@/components/RoiCalculator";

export const metadata: Metadata = generatePageMetadata({
  title: "AI Agent Cost Exposure Calculator — AI Identity",
  description:
    "Calculate your organization's financial risk from unmonitored AI agents. See how much ungoverned API spending could cost you and how AI Identity's spending controls prevent runaway costs.",
  path: "/roi-calculator",
});

export default function RoiCalculatorPage() {
  return <RoiCalculator />;
}
