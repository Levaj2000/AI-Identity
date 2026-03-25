import {
  AIIdentityLogo1, AIIdentityLogo2, AIIdentityLogo3,
  AIIdentityIcon1, AIIdentityIcon2, AIIdentityIcon3,
  AIIdentityLogo4, AIIdentityIcon4,
  AIIdentityLogo5, AIIdentityIcon5
} from '../components/AIIdentityLogo';
import { GridBackground, AnimatedGridBackground } from '../components/GridBackground';

export default function Brand() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] p-8 overflow-y-auto">
      <div className="max-w-7xl mx-auto space-y-16 pt-24 pb-16">

        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-5xl font-bold text-white">AI Identity - Brand Assets</h1>
          <p className="text-xl text-white/60">Official Brand Identity</p>
          <div className="flex items-center justify-center gap-8 pt-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-[#00FFC2] rounded"></div>
              <div className="text-left">
                <div className="text-xs text-white/40 uppercase tracking-wider">Cyber Cyan</div>
                <div className="text-sm font-mono text-white">#00FFC2</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-[#0A0A0B] border border-white/20 rounded"></div>
              <div className="text-left">
                <div className="text-xs text-white/40 uppercase tracking-wider">Obsidian</div>
                <div className="text-sm font-mono text-white">#0A0A0B</div>
              </div>
            </div>
          </div>
        </div>

        {/* Official Logo - Featured Section */}
        <section className="space-y-8">
          <div className="text-center space-y-2">
            <div className="inline-block px-4 py-1.5 bg-[#00FFC2]/10 border border-[#00FFC2] rounded-full mb-4">
              <span className="text-sm font-bold text-[#00FFC2] uppercase tracking-wider">✓ Official Logo</span>
            </div>
            <h2 className="text-4xl font-bold text-white">Cyber Cyan - Three Bars</h2>
            <p className="text-white/50">Clean, modern, data-driven identity</p>
          </div>

          {/* Large showcase */}
          <div className="relative bg-[#0A0A0B] border-2 border-[#00FFC2] rounded-2xl p-20 overflow-hidden shadow-2xl shadow-[#00FFC2]/20">
            <AnimatedGridBackground animationType="pulse" opacity={0.15} />
            <div className="relative z-10">
              <div className="flex items-center justify-center">
                <AIIdentityLogo5 variant="primary" className="w-[600px] h-auto" />
              </div>
            </div>
          </div>

          {/* Logo usage examples */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
              <div className="flex items-center justify-center h-32">
                <AIIdentityLogo5 variant="primary" className="w-[280px] h-auto" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-[#00FFC2]">Cyber Cyan</p>
                <p className="text-xs text-white/40">Primary - Light backgrounds</p>
              </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-xl p-8 space-y-4">
              <div className="flex items-center justify-center h-32">
                <AIIdentityLogo5 variant="dark" className="w-[280px] h-auto" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-gray-900">Obsidian</p>
                <p className="text-xs text-gray-500">Dark - Light backgrounds</p>
              </div>
            </div>

            <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 space-y-4">
              <div className="flex items-center justify-center h-32">
                <AIIdentityLogo5 variant="light" className="w-[280px] h-auto" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-white">White</p>
                <p className="text-xs text-white/40">Light - Dark backgrounds</p>
              </div>
            </div>
          </div>

          {/* Icon only version */}
          <div className="space-y-4">
            <h3 className="text-xl font-bold text-white text-center">Icon Mark</h3>
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 flex items-center justify-center">
                <AIIdentityIcon5 variant="primary" className="w-24 h-auto" />
              </div>
              <div className="bg-white border border-gray-200 rounded-xl p-8 flex items-center justify-center">
                <AIIdentityIcon5 variant="dark" className="w-24 h-auto" />
              </div>
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 flex items-center justify-center">
                <AIIdentityIcon5 variant="light" className="w-24 h-auto" />
              </div>
              <div className="bg-gradient-to-br from-purple-600 to-blue-600 rounded-xl p-8 flex items-center justify-center">
                <AIIdentityIcon5 variant="light" className="w-24 h-auto" />
              </div>
            </div>
          </div>
        </section>

        {/* Official Background Pattern */}
        <section className="space-y-8">
          <div className="text-center space-y-2">
            <div className="inline-block px-4 py-1.5 bg-[#00FFC2]/10 border border-[#00FFC2] rounded-full mb-4">
              <span className="text-sm font-bold text-[#00FFC2] uppercase tracking-wider">✓ Official Pattern</span>
            </div>
            <h2 className="text-4xl font-bold text-white">Animated Grid - Pulse</h2>
            <p className="text-white/50">Cybersecurity-inspired background with animated pulses</p>
          </div>

          {/* Large showcase */}
          <div className="relative bg-[#0A0A0B] border-2 border-[#00FFC2] rounded-2xl overflow-hidden h-96 shadow-2xl shadow-[#00FFC2]/20">
            <AnimatedGridBackground animationType="pulse" opacity={0.3} />
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="text-center space-y-2 bg-[#0A0A0B]/80 backdrop-blur-xl border border-[#00FFC2]/20 rounded-2xl px-12 py-8">
                <h3 className="text-2xl font-bold text-white">Pulse Animation</h3>
                <p className="text-white/60">Organic, living grid effect</p>
              </div>
            </div>
          </div>
        </section>

        {/* Additional Logo Variations - Archive */}
        <section className="space-y-8 pt-12 border-t border-white/10">
          <div className="text-center space-y-2">
            <h2 className="text-3xl font-bold text-white/40">Archived Concepts</h2>
            <p className="text-white/30">Alternative logo explorations</p>
          </div>

          {/* Logo 1: Infinite Loop */}
          <div className="space-y-6">
            <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-16 overflow-hidden">
              <GridBackground variant="dots" opacity={0.08} />
              <div className="relative z-10">
                <div className="flex items-center justify-center pb-6">
                  <AIIdentityLogo1 variant="primary" className="w-[500px] h-auto" />
                </div>
                <div className="text-center space-y-2">
                  <h3 className="text-2xl font-bold text-white">Concept 1: Infinite Loop</h3>
                  <p className="text-white/60">Overlapping circles representing continuous identity verification and infinite scalability</p>
                </div>
              </div>
            </div>

            {/* Color variations for Logo 1 */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo1 variant="primary" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">Cyber Cyan</p>
              </div>
              <div className="bg-[#0A0A0B] border border-white/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo1 variant="light" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">White</p>
              </div>
              <div className="bg-white border border-black/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo1 variant="dark" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-black/50">Obsidian</p>
              </div>
            </div>
          </div>

          {/* Logo 2: Set Theory */}
          <div className="space-y-6">
            <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-16 overflow-hidden">
              <GridBackground variant="lines" opacity={0.08} />
              <div className="relative z-10">
                <div className="flex items-center justify-center pb-6">
                  <AIIdentityLogo2 variant="primary" className="w-[500px] h-auto" />
                </div>
                <div className="text-center space-y-2">
                  <h3 className="text-2xl font-bold text-white">Concept 2: Set Theory</h3>
                  <p className="text-white/60">Mathematical intersection symbol representing the convergence of AI and identity</p>
                </div>
              </div>
            </div>

            {/* Color variations for Logo 2 */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo2 variant="primary" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">Cyber Cyan</p>
              </div>
              <div className="bg-[#0A0A0B] border border-white/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo2 variant="light" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">White</p>
              </div>
              <div className="bg-white border border-black/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo2 variant="dark" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-black/50">Obsidian</p>
              </div>
            </div>
          </div>

          {/* Logo 3: Neural Grid */}
          <div className="space-y-6">
            <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-16 overflow-hidden">
              <GridBackground variant="circuit" opacity={0.1} />
              <div className="relative z-10">
                <div className="flex items-center justify-center pb-6">
                  <AIIdentityLogo3 variant="primary" className="w-[500px] h-auto" />
                </div>
                <div className="text-center space-y-2">
                  <h3 className="text-2xl font-bold text-white">Concept 3: Neural Grid</h3>
                  <p className="text-white/60">Connected nodes forming an abstract network, symbolizing distributed AI agent authentication</p>
                </div>
              </div>
            </div>

            {/* Color variations for Logo 3 */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo3 variant="primary" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">Cyber Cyan</p>
              </div>
              <div className="bg-[#0A0A0B] border border-white/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo3 variant="light" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">White</p>
              </div>
              <div className="bg-white border border-black/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo3 variant="dark" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-black/50">Obsidian</p>
              </div>
            </div>
          </div>

          {/* Logo 4: Quantum Wave */}
          <div className="space-y-6">
            <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-16 overflow-hidden">
              <GridBackground variant="circuit" opacity={0.1} />
              <div className="relative z-10">
                <div className="flex items-center justify-center pb-6">
                  <AIIdentityLogo4 variant="primary" className="w-[500px] h-auto" />
                </div>
                <div className="text-center space-y-2">
                  <h3 className="text-2xl font-bold text-white">Concept 4: Quantum Wave</h3>
                  <p className="text-white/60">Waveform symbolizing the quantum nature of AI identity</p>
                </div>
              </div>
            </div>

            {/* Color variations for Logo 4 */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo4 variant="primary" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">Cyber Cyan</p>
              </div>
              <div className="bg-[#0A0A0B] border border-white/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo4 variant="light" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">White</p>
              </div>
              <div className="bg-white border border-black/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo4 variant="dark" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-black/50">Obsidian</p>
              </div>
            </div>
          </div>

          {/* Logo 5: Binary Matrix */}
          <div className="space-y-6">
            <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-16 overflow-hidden">
              <GridBackground variant="circuit" opacity={0.1} />
              <div className="relative z-10">
                <div className="flex items-center justify-center pb-6">
                  <AIIdentityLogo5 variant="primary" className="w-[500px] h-auto" />
                </div>
                <div className="text-center space-y-2">
                  <h3 className="text-2xl font-bold text-white">Concept 5: Binary Matrix</h3>
                  <p className="text-white/60">Matrix of binary digits symbolizing the digital nature of AI identity</p>
                </div>
              </div>
            </div>

            {/* Color variations for Logo 5 */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo5 variant="primary" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">Cyber Cyan</p>
              </div>
              <div className="bg-[#0A0A0B] border border-white/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo5 variant="light" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-white/50">White</p>
              </div>
              <div className="bg-white border border-black/10 rounded-xl p-8 space-y-4">
                <div className="flex items-center justify-center">
                  <AIIdentityLogo5 variant="dark" className="w-full h-auto" />
                </div>
                <p className="text-center text-sm text-black/50">Obsidian</p>
              </div>
            </div>
          </div>
        </section>

        {/* Icon-Only Versions */}
        <section className="space-y-8">
          <div className="text-center space-y-2">
            <h2 className="text-3xl font-bold text-[#00FFC2]">Icon-Only Marks</h2>
            <p className="text-white/50">Compact versions for favicons, app icons, and small spaces</p>
          </div>

          <div className="grid grid-cols-3 gap-8">
            {/* Icon 1 */}
            <div className="space-y-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-12">
                <div className="flex items-center justify-center">
                  <AIIdentityIcon1 variant="primary" className="w-32 h-32" />
                </div>
              </div>
              <p className="text-center text-sm text-white/60">Infinite Loop Icon</p>
            </div>

            {/* Icon 2 */}
            <div className="space-y-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-12">
                <div className="flex items-center justify-center">
                  <AIIdentityIcon2 variant="primary" className="w-32 h-32" />
                </div>
              </div>
              <p className="text-center text-sm text-white/60">Set Theory Icon</p>
            </div>

            {/* Icon 3 */}
            <div className="space-y-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-12">
                <div className="flex items-center justify-center">
                  <AIIdentityIcon3 variant="primary" className="w-32 h-32" />
                </div>
              </div>
              <p className="text-center text-sm text-white/60">Neural Grid Icon</p>
            </div>

            {/* Icon 4 */}
            <div className="space-y-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-12">
                <div className="flex items-center justify-center">
                  <AIIdentityIcon4 variant="primary" className="w-32 h-32" />
                </div>
              </div>
              <p className="text-center text-sm text-white/60">Quantum Wave Icon</p>
            </div>

            {/* Icon 5 */}
            <div className="space-y-4">
              <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-2xl p-12">
                <div className="flex items-center justify-center">
                  <AIIdentityIcon5 variant="primary" className="w-32 h-32" />
                </div>
              </div>
              <p className="text-center text-sm text-white/60">Binary Matrix Icon</p>
            </div>
          </div>
        </section>

        {/* Hero Examples */}
        <section className="space-y-8">
          <div className="text-center space-y-2">
            <h2 className="text-3xl font-bold text-[#00FFC2]">In Context</h2>
            <p className="text-white/50">How the logos work in real hero sections</p>
          </div>

          {/* Example 1 */}
          <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/30 rounded-2xl overflow-hidden" style={{ height: '500px' }}>
            <AnimatedGridBackground opacity={0.06} />
            <div className="relative z-10 flex flex-col items-center justify-center h-full space-y-8 px-8">
              <AIIdentityLogo1 variant="primary" className="w-[400px] h-auto" />
              <h1 className="text-5xl font-bold text-white text-center max-w-4xl leading-tight">
                Okta for AI agents, not humans
              </h1>
              <p className="text-lg text-white/70 text-center max-w-2xl">
                Deploy in 15 minutes. Give each AI agent its own cryptographic key.
              </p>
              <button className="bg-[#00FFC2] text-[#0A0A0B] px-8 py-3 rounded-lg font-bold hover:bg-[#00FFC2]/90 transition-colors">
                Get Started
              </button>
            </div>
          </div>

          {/* Example 2 */}
          <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/30 rounded-2xl overflow-hidden" style={{ height: '500px' }}>
            <GridBackground variant="circuit" opacity={0.08} />
            <div className="relative z-10 flex flex-col items-center justify-center h-full space-y-8 px-8">
              <AIIdentityLogo2 variant="primary" className="w-[400px] h-auto" />
              <h1 className="text-5xl font-bold text-white text-center max-w-4xl leading-tight">
                Identity & access management for AI
              </h1>
              <p className="text-lg text-white/70 text-center max-w-2xl">
                Architecture aligned with SOC 2 controls with HMAC audit chains. Know which agent made that $400 API call.
              </p>
              <button className="bg-[#00FFC2] text-[#0A0A0B] px-8 py-3 rounded-lg font-bold hover:bg-[#00FFC2]/90 transition-colors">
                Get Started
              </button>
            </div>
          </div>
        </section>

        {/* Background Patterns */}
        <section className="space-y-8">
          <h2 className="text-3xl font-bold text-[#00FFC2] text-center">Background Patterns</h2>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Dot Grid */}
            <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl overflow-hidden" style={{ height: '300px' }}>
              <GridBackground variant="dots" opacity={0.15} />
              <div className="relative z-10 flex items-center justify-center h-full">
                <div className="text-center space-y-2 p-6 backdrop-blur-sm bg-[#0A0A0B]/50 rounded-lg border border-[#00FFC2]/10">
                  <h3 className="text-xl font-bold text-white">Dot Grid</h3>
                  <p className="text-white/60 text-sm">Subtle and minimal</p>
                </div>
              </div>
            </div>

            {/* Line Grid */}
            <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl overflow-hidden" style={{ height: '300px' }}>
              <GridBackground variant="lines" opacity={0.12} />
              <div className="relative z-10 flex items-center justify-center h-full">
                <div className="text-center space-y-2 p-6 backdrop-blur-sm bg-[#0A0A0B]/50 rounded-lg border border-[#00FFC2]/10">
                  <h3 className="text-xl font-bold text-white">Line Grid</h3>
                  <p className="text-white/60 text-sm">Clean geometric</p>
                </div>
              </div>
            </div>

            {/* Circuit Grid */}
            <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl overflow-hidden" style={{ height: '300px' }}>
              <GridBackground variant="circuit" opacity={0.2} />
              <div className="relative z-10 flex items-center justify-center h-full">
                <div className="text-center space-y-2 p-6 backdrop-blur-sm bg-[#0A0A0B]/50 rounded-lg border border-[#00FFC2]/10">
                  <h3 className="text-xl font-bold text-white">Circuit Grid</h3>
                  <p className="text-white/60 text-sm">Technical nodes</p>
                </div>
              </div>
            </div>

            {/* Animated Grid */}
            <div className="relative bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl overflow-hidden" style={{ height: '300px' }}>
              <AnimatedGridBackground opacity={0.1} />
              <div className="relative z-10 flex items-center justify-center h-full">
                <div className="text-center space-y-2 p-6 backdrop-blur-sm bg-[#0A0A0B]/50 rounded-lg border border-[#00FFC2]/10">
                  <h3 className="text-xl font-bold text-white">Animated Grid</h3>
                  <p className="text-white/60 text-sm">Pulse animation</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Design Philosophy */}
        <section className="space-y-8">
          <h2 className="text-3xl font-bold text-[#00FFC2] text-center">Design Philosophy</h2>

          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
              <div className="w-12 h-12 bg-[#00FFC2]/10 rounded-lg flex items-center justify-center">
                <span className="text-2xl">∞</span>
              </div>
              <h3 className="text-xl font-bold text-white">Abstract & Symbolic</h3>
              <p className="text-white/60 text-sm leading-relaxed">
                No literal security icons. Pure geometric forms that suggest continuity, connection, and mathematical precision.
              </p>
            </div>

            <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
              <div className="w-12 h-12 bg-[#00FFC2]/10 rounded-lg flex items-center justify-center">
                <span className="text-2xl">─</span>
              </div>
              <h3 className="text-xl font-bold text-white">Minimalist</h3>
              <p className="text-white/60 text-sm leading-relaxed">
                Clean lines, essential forms only. Every element serves a purpose. High-end tech aesthetic without excess.
              </p>
            </div>

            <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
              <div className="w-12 h-12 bg-[#00FFC2]/10 rounded-lg flex items-center justify-center">
                <span className="text-2xl text-[#00FFC2]">◆</span>
              </div>
              <h3 className="text-xl font-bold text-white">Futuristic</h3>
              <p className="text-white/60 text-sm leading-relaxed">
                Cyber cyan accent on obsidian black. Designed for the next generation of AI-first platforms.
              </p>
            </div>
          </div>
        </section>

        {/* Usage Guidelines */}
        <section className="space-y-8">
          <h2 className="text-3xl font-bold text-[#00FFC2] text-center">Usage Guidelines</h2>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-[#0A0A0B] border border-[#00FFC2]/20 rounded-xl p-8 space-y-4">
              <h3 className="text-xl font-bold text-white">✓ Do</h3>
              <ul className="space-y-2 text-white/60 text-sm leading-relaxed">
                <li>• Use cyber cyan (#00FFC2) on dark backgrounds</li>
                <li>• Maintain minimum clear space (1/2 logo height)</li>
                <li>• Use icon-only versions for favicons and small spaces</li>
                <li>• Keep background patterns subtle (0.08-0.15 opacity)</li>
                <li>• Pair with Inter font family for consistency</li>
              </ul>
            </div>

            <div className="bg-[#0A0A0B] border border-red-500/20 rounded-xl p-8 space-y-4">
              <h3 className="text-xl font-bold text-red-400">✗ Don't</h3>
              <ul className="space-y-2 text-white/60 text-sm leading-relaxed">
                <li>• Don't rotate, skew, or distort the logos</li>
                <li>• Don't use low contrast color combinations</li>
                <li>• Don't add effects (shadows, gradients, etc.)</li>
                <li>• Don't alter proportions or spacing</li>
                <li>• Don't use security icons (shields, locks, keys)</li>
              </ul>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
