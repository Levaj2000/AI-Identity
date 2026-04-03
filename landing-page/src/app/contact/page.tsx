import type { Metadata } from "next";
import { generatePageMetadata } from "@/lib/metadata";
import ContactContent from "./contact-content";

export const metadata: Metadata = generatePageMetadata({
  title: "Contact AI Identity",
  description: "Get in touch with the AI Identity team. Schedule a demo, ask a question, or explore design partnership opportunities.",
  path: "/contact",
});

export default function ContactPage() {
  return <ContactContent />;
}
