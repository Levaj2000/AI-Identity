import Nav from "./landing/Nav";
import Hero from "./landing/Hero";
import SocialProof from "./landing/SocialProof";
import HowItWorksSection from "./landing/HowItWorksSection";
import Features from "./landing/Features";
import DashboardPreview from "./landing/DashboardPreview";
import ComplianceSection from "./landing/ComplianceSection";
import ForensicsSection from "./landing/ForensicsSection";
import SecuritySection from "./landing/SecuritySection";
import IntegrationsSection from "./landing/IntegrationsSection";
import Pricing from "./landing/Pricing";
import FinalCTA from "./landing/FinalCTA";
import Footer from "./landing/Footer";
import { ParticleBackground } from "./landing/ParticleBackground";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0F1724] text-white font-['Inter',sans-serif] relative">
      <ParticleBackground />
      <Nav />
      <Hero />
      <SocialProof />
      <HowItWorksSection />
      <Features />
      <DashboardPreview />
      <ComplianceSection />
      <ForensicsSection />
      <SecuritySection />
      <IntegrationsSection />
      <Pricing />
      <FinalCTA />
      <Footer />
    </div>
  );
}
