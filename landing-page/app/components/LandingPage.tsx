import { motion } from "framer-motion";
import Nav from "./landing/Nav";
import Hero from "./landing/Hero";
import SocialProof from "./landing/SocialProof";
import HowItWorksSection from "./landing/HowItWorksSection";
import Features from "./landing/Features";
import DashboardPreview from "./landing/DashboardPreview";
import SecuritySection from "./landing/SecuritySection";
import IntegrationsSection from "./landing/IntegrationsSection";
import Pricing from "./landing/Pricing";
import FinalCTA from "./landing/FinalCTA";
import Footer from "./landing/Footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-white font-['Inter',sans-serif]">
      <Nav />
      <Hero />
      <SocialProof />
      <HowItWorksSection />
      <Features />
      <DashboardPreview />
      <SecuritySection />
      <IntegrationsSection />
      <Pricing />
      <FinalCTA />
      <Footer />
    </div>
  );
}
