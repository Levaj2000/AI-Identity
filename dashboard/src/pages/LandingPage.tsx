import { LandingNav } from './landing/LandingNav'
import { HeroSection } from './landing/HeroSection'
import { ProblemSection } from './landing/ProblemSection'
import { StatsSection } from './landing/StatsSection'
import { SolutionSection } from './landing/SolutionSection'
import { ArchitectureSection } from './landing/ArchitectureSection'
import { CodeSection } from './landing/CodeSection'
import { SocialProofSection } from './landing/SocialProofSection'
import { CTASection } from './landing/CTASection'
import { LandingFooter } from './landing/LandingFooter'

/**
 * Public marketing landing page for ai-identity.co.
 * Loads at "/" — no sidebar, no auth required.
 */
export function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-gray-900 dark:bg-slate-950 dark:text-slate-100">
      <LandingNav />
      <main>
        <HeroSection />
        <ProblemSection />
        <StatsSection />
        <SolutionSection />
        <ArchitectureSection />
        <CodeSection />
        <SocialProofSection />
        <CTASection />
      </main>
      <LandingFooter />
    </div>
  )
}
