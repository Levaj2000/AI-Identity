import { AIIdentityLogo, AIIdentityLogoCompact } from './AIIdentityLogo';
import { GridBackground, AnimatedGridBackground } from './GridBackground';

export function LogoShowcase() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] p-8 overflow-y-auto">
      <div className="max-w-7xl mx-auto space-y-16">

        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-[#F7F1E3]">AI Identity - Brand Assets</h1>
          <p className="text-lg text-[#F7F1E3]/70">Logo variations and background patterns</p>
        </div>

        {/* Logo Variations */}
        <section className="space-y-8">
          <h2 className="text-2xl font-bold text-[#00FFC2]">Logo Variations</h2>

          {/* Primary Logo on Dark */}
          <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-lg p-12 space-y-4">
            <div className="flex items-center justify-center">
              <AIIdentityLogo variant="primary" className="w-[400px] h-auto" />
            </div>
            <p className="text-center text-sm text-[#F7F1E3]/60">Primary Logo (#00FFC2) - Main Usage</p>
          </div>

          {/* Light Logo on Dark */}
          <div className="bg-[#0A0A0B] border border-[#F7F1E3]/20 rounded-lg p-12 space-y-4">
            <div className="flex items-center justify-center">
              <AIIdentityLogo variant="light" className="w-[400px] h-auto" />
            </div>
            <p className="text-center text-sm text-[#F7F1E3]/60">Light Logo (#F7F1E3) - Alternative</p>
          </div>

          {/* Dark Logo on Light */}
          <div className="bg-[#F7F1E3] border border-[#0A0A0B]/20 rounded-lg p-12 space-y-4">
            <div className="flex items-center justify-center">
              <AIIdentityLogo variant="dark" className="w-[400px] h-auto" />
            </div>
            <p className="text-center text-sm text-[#0A0A0B]/60">Dark Logo (#0A0A0B) - Light Backgrounds</p>
          </div>

          {/* Compact Logos */}
          <div className="grid grid-cols-3 gap-6">
            <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-lg p-8 space-y-4">
              <div className="flex items-center justify-center">
                <AIIdentityLogoCompact variant="primary" className="w-24 h-24" />
              </div>
              <p className="text-center text-xs text-[#F7F1E3]/60">Compact Primary</p>
            </div>
            <div className="bg-[#0A0A0B] border border-[#F7F1E3]/20 rounded-lg p-8 space-y-4">
              <div className="flex items-center justify-center">
                <AIIdentityLogoCompact variant="light" className="w-24 h-24" />
              </div>
              <p className="text-center text-xs text-[#F7F1E3]/60">Compact Light</p>
            </div>
            <div className="bg-[#F7F1E3] border border-[#0A0A0B]/20 rounded-lg p-8 space-y-4">
              <div className="flex items-center justify-center">
                <AIIdentityLogoCompact variant="dark" className="w-24 h-24" />
              </div>
              <p className="text-center text-xs text-[#0A0A0B]/60">Compact Dark</p>
            </div>
          </div>
        </section>

        {/* Background Patterns */}
        <section className="space-y-8">
          <h2 className="text-2xl font-bold text-[#00FFC2]">Background Patterns</h2>

          {/* Dot Grid */}
          <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-lg overflow-hidden" style={{ height: '400px' }}>
            <GridBackground variant="dots" opacity={0.15} />
            <div className="relative z-10 flex items-center justify-center h-full">
              <div className="text-center space-y-4 p-8 backdrop-blur-sm bg-[#0A0A0B]/50 rounded-lg border border-[#00FFC2]/10">
                <h3 className="text-2xl font-bold text-[#F7F1E3]">Dot Grid Pattern</h3>
                <p className="text-[#F7F1E3]/70">Subtle and minimal</p>
              </div>
            </div>
          </div>

          {/* Line Grid */}
          <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-lg overflow-hidden" style={{ height: '400px' }}>
            <GridBackground variant="lines" opacity={0.12} />
            <div className="relative z-10 flex items-center justify-center h-full">
              <div className="text-center space-y-4 p-8 backdrop-blur-sm bg-[#0A0A0B]/50 rounded-lg border border-[#00FFC2]/10">
                <h3 className="text-2xl font-bold text-[#F7F1E3]">Line Grid Pattern</h3>
                <p className="text-[#F7F1E3]/70">Clean geometric grid</p>
              </div>
            </div>
          </div>

          {/* Circuit Grid */}
          <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-lg overflow-hidden" style={{ height: '400px' }}>
            <GridBackground variant="circuit" opacity={0.2} />
            <div className="relative z-10 flex items-center justify-center h-full">
              <div className="text-center space-y-4 p-8 backdrop-blur-sm bg-[#0A0A0B]/50 rounded-lg border border-[#00FFC2]/10">
                <h3 className="text-2xl font-bold text-[#F7F1E3]">Circuit Grid Pattern</h3>
                <p className="text-[#F7F1E3]/70">Technical with node connections</p>
              </div>
            </div>
          </div>

          {/* Animated Grid */}
          <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-lg overflow-hidden" style={{ height: '400px' }}>
            <AnimatedGridBackground opacity={0.1} />
            <div className="relative z-10 flex items-center justify-center h-full">
              <div className="text-center space-y-4 p-8 backdrop-blur-sm bg-[#0A0A0B]/50 rounded-lg border border-[#00FFC2]/10">
                <h3 className="text-2xl font-bold text-[#F7F1E3]">Animated Grid Pattern</h3>
                <p className="text-[#F7F1E3]/70">Subtle pulse animation with glowing nodes</p>
              </div>
            </div>
          </div>

          {/* Hero Example */}
          <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/30 rounded-lg overflow-hidden" style={{ height: '600px' }}>
            <AnimatedGridBackground opacity={0.08} />
            <div className="relative z-10 flex flex-col items-center justify-center h-full space-y-8 px-8">
              <AIIdentityLogo variant="primary" className="w-[500px] h-auto" />
              <h1 className="text-6xl font-bold text-[#F7F1E3] text-center max-w-4xl leading-tight">
                Okta for AI agents, not humans
              </h1>
              <p className="text-xl text-[#F7F1E3]/80 text-center max-w-3xl">
                Deploy in 15 minutes, not 15 weeks. Give each AI agent its own cryptographic API key, scoped permissions, and tamper-proof audit trail.
              </p>
              <div className="flex gap-4">
                <button className="bg-[#00FFC2] text-[#0A0A0B] px-8 py-3 rounded font-semibold hover:bg-[#00FFC2]/90 transition-colors">
                  Get Started
                </button>
                <button className="border border-[#00FFC2] text-[#00FFC2] px-8 py-3 rounded font-semibold hover:bg-[#00FFC2]/10 transition-colors">
                  Learn More
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Usage Guidelines */}
        <section className="space-y-8 pb-16">
          <h2 className="text-2xl font-bold text-[#00FFC2]">Usage Guidelines</h2>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-lg p-6 space-y-3">
              <h3 className="text-lg font-bold text-[#F7F1E3]">✓ Do</h3>
              <ul className="space-y-2 text-[#F7F1E3]/70 text-sm">
                <li>• Use primary (#00FFC2) logo on dark backgrounds</li>
                <li>• Maintain clear space around logo</li>
                <li>• Use compact logo for small spaces (favicons, etc.)</li>
                <li>• Keep background patterns subtle (opacity 0.1-0.2)</li>
              </ul>
            </div>

            <div className="bg-[#0A0A0B] border border-red-500/20 rounded-lg p-6 space-y-3">
              <h3 className="text-lg font-bold text-red-400">✗ Don't</h3>
              <ul className="space-y-2 text-[#F7F1E3]/70 text-sm">
                <li>• Don't rotate or distort the logo</li>
                <li>• Don't use low contrast combinations</li>
                <li>• Don't make background patterns too prominent</li>
                <li>• Don't alter logo proportions or colors</li>
              </ul>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
