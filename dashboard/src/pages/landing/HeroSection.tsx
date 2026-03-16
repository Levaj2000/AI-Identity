import { useRef, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMousePosition } from '../../hooks/useMousePosition'
import { useTypewriter } from '../../hooks/useTypewriter'

/* ── Animated SVG network background with mouse-reactive parallax ── */

function NetworkBackground({ mouseX, mouseY }: { mouseX: number; mouseY: number }) {
  // Hexagonal node positions (viewBox 800x500) — split into 3 depth layers
  const nodes = [
    { x: 120, y: 80, agent: false, depth: 0 },
    { x: 300, y: 60, agent: true, depth: 1 },
    { x: 500, y: 40, agent: false, depth: 2 },
    { x: 680, y: 90, agent: false, depth: 0 },
    { x: 80, y: 260, agent: false, depth: 1 },
    { x: 250, y: 220, agent: false, depth: 2 },
    { x: 400, y: 250, agent: true, depth: 0 },
    { x: 580, y: 200, agent: false, depth: 1 },
    { x: 720, y: 280, agent: true, depth: 2 },
    { x: 160, y: 420, agent: false, depth: 0 },
    { x: 350, y: 400, agent: false, depth: 1 },
    { x: 550, y: 440, agent: false, depth: 2 },
    { x: 700, y: 420, agent: false, depth: 0 },
  ]

  // Connections between nearby nodes (indices)
  const edges = [
    [0, 1],
    [1, 2],
    [2, 3],
    [0, 5],
    [1, 5],
    [1, 6],
    [2, 7],
    [3, 7],
    [4, 5],
    [5, 6],
    [6, 7],
    [7, 8],
    [4, 9],
    [5, 10],
    [6, 10],
    [6, 11],
    [7, 11],
    [8, 12],
    [9, 10],
    [10, 11],
    [11, 12],
  ]

  // Parallax offsets per depth layer
  const depthMultiplier = [3, 7, 12]

  const getOffset = (depth: number) => ({
    x: mouseX * depthMultiplier[depth],
    y: mouseY * depthMultiplier[depth],
  })

  return (
    <svg
      viewBox="0 0 800 500"
      className="absolute inset-0 h-full w-full"
      preserveAspectRatio="xMidYMid slice"
    >
      {/* Connecting lines — move with depth of connected nodes */}
      <g style={{ animation: 'drift-1 25s ease-in-out infinite' }}>
        {edges.map(([a, b], i) => {
          const offA = getOffset(nodes[a].depth)
          const offB = getOffset(nodes[b].depth)
          return (
            <line
              key={`e${i}`}
              x1={nodes[a].x + offA.x}
              y1={nodes[a].y + offA.y}
              x2={nodes[b].x + offB.x}
              y2={nodes[b].y + offB.y}
              className="stroke-indigo-500/10 dark:stroke-indigo-400/10"
              strokeWidth="1"
              strokeDasharray="4 6"
              style={{ animation: `line-dash ${8 + (i % 4) * 2}s linear infinite` }}
            />
          )
        })}
      </g>

      {/* Hexagonal nodes — each layer moves at different speed */}
      {nodes.map((node, i) => {
        const off = getOffset(node.depth)
        const nx = node.x + off.x
        const ny = node.y + off.y
        const s = 12
        const hex = `${nx},${ny - s} ${nx + s * 0.866},${ny - s / 2} ${nx + s * 0.866},${ny + s / 2} ${nx},${ny + s} ${nx - s * 0.866},${ny + s / 2} ${nx - s * 0.866},${ny - s / 2}`
        return (
          <g key={`n${i}`}>
            <polygon
              points={hex}
              fill="none"
              className="stroke-indigo-500/20 dark:stroke-indigo-400/20"
              strokeWidth="1"
              style={{
                animation: `node-pulse ${4 + (i % 3) * 1.5}s ease-in-out infinite`,
                animationDelay: `${i * 0.3}s`,
              }}
            />
            {node.agent && (
              <circle
                cx={nx}
                cy={ny}
                r="3"
                fill="#F59E0B"
                opacity="0.7"
                style={{
                  animation: `node-pulse 3s ease-in-out infinite`,
                  animationDelay: `${i * 0.5}s`,
                }}
              />
            )}
          </g>
        )
      })}
    </svg>
  )
}

/* ── Hero section ───────────────────────────────────────────────── */

export function HeroSection() {
  const { ref: mouseRef, position } = useMousePosition()
  const [entered, setEntered] = useState(false)

  // Trigger entrance animations after mount
  useEffect(() => {
    const t = setTimeout(() => setEntered(true), 100)
    return () => clearTimeout(t)
  }, [])

  // Typewriter: line 1 types first, then line 2
  const line1 = useTypewriter({
    text: 'Every agent gets',
    speed: 55,
    startDelay: 600,
    trigger: entered,
  })
  const line2 = useTypewriter({
    text: 'an identity.',
    speed: 65,
    startDelay: 200,
    trigger: line1.isComplete,
  })

  // Spotlight CSS custom properties
  const spotlightRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!spotlightRef.current) return
    const pctX = ((position.x + 1) / 2) * 100
    const pctY = ((position.y + 1) / 2) * 100
    spotlightRef.current.style.setProperty('--spot-x', `${pctX}%`)
    spotlightRef.current.style.setProperty('--spot-y', `${pctY}%`)
  }, [position.x, position.y])

  // Stagger delays for entrance
  const stagger = (index: number) => ({
    transition: 'opacity 0.7s ease-out, transform 0.7s ease-out',
    transitionDelay: `${200 + index * 150}ms`,
    opacity: entered ? 1 : 0,
    transform: entered ? 'translateY(0)' : 'translateY(24px)',
  })

  return (
    <section
      ref={mouseRef}
      className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 pt-20"
    >
      {/* Cursor spotlight overlay */}
      <div
        ref={spotlightRef}
        className="cursor-spotlight pointer-events-none absolute inset-0 z-[1]"
      />

      {/* Radial gradient overlay */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(79,70,229,0.08),transparent_70%)]" />

      {/* Mouse-reactive network */}
      <NetworkBackground mouseX={position.x} mouseY={position.y} />

      {/* Content — staggered entrance */}
      <div className="relative z-10 mx-auto max-w-3xl text-center">
        {/* Eyebrow */}
        <div style={stagger(0)}>
          <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/5 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-indigo-500 dark:text-indigo-400">
            <span
              className="h-1.5 w-1.5 rounded-full bg-indigo-500 dark:bg-indigo-400"
              style={{ animation: 'node-pulse 2s ease-in-out infinite' }}
            />
            Identity for AI Agents
          </p>
        </div>

        {/* Typewriter headline */}
        <div style={stagger(1)}>
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight text-gray-900 dark:text-white sm:text-5xl md:text-6xl">
            <span className="block">
              {line1.displayText}
              <span
                className="inline-block w-[3px] translate-y-[2px] bg-indigo-500 dark:bg-indigo-400"
                style={{
                  height: '0.85em',
                  animation: 'cursor-blink 1.06s step-end infinite',
                  opacity:
                    !line1.isComplete && line1.cursorVisible
                      ? 1
                      : line1.isComplete && !line2.displayText
                        ? 1
                        : 0,
                }}
              />
            </span>
            <span
              className={`block bg-gradient-to-r from-indigo-500 to-indigo-400 bg-clip-text text-transparent ${
                line2.isComplete ? 'animate-[text-glow_1.5s_ease-out_0.2s_1]' : ''
              }`}
            >
              {line2.displayText}
              <span
                className="inline-block w-[3px] translate-y-[2px] bg-indigo-500 dark:bg-indigo-400"
                style={{
                  height: '0.85em',
                  animation: 'cursor-blink 1.06s step-end infinite',
                  opacity: line1.isComplete && line2.cursorVisible ? 1 : 0,
                }}
              />
            </span>
          </h1>
        </div>

        {/* Subheadline */}
        <div style={stagger(2)}>
          <p className="mx-auto mt-6 max-w-xl text-lg text-gray-500 dark:text-slate-400">
            Per-agent API keys, scoped permissions, and tamper-proof audit trails. Deploy in 15
            minutes, not 15 weeks.
          </p>
        </div>

        {/* CTAs */}
        <div style={stagger(3)}>
          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              to="/app"
              className="group inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-8 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all duration-200 hover:scale-[1.03] hover:bg-indigo-500 hover:shadow-indigo-500/40 active:scale-[0.98]"
            >
              Get Started Free
              <svg
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
              >
                <path
                  fillRule="evenodd"
                  d="M3 10a.75.75 0 01.75-.75h10.638L11.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.04-1.08l3.158-2.96H3.75A.75.75 0 013 10z"
                  clipRule="evenodd"
                />
              </svg>
            </Link>
            <a
              href="https://ai-identity-api.onrender.com/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white/50 px-8 py-3.5 text-sm font-semibold text-gray-700 backdrop-blur-sm transition-all duration-200 hover:scale-[1.02] hover:bg-white hover:text-gray-900 active:scale-[0.98] dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              View API Docs
            </a>
          </div>
        </div>

        {/* API key preview */}
        <div style={stagger(4)}>
          <div className="mt-16 inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white/50 px-5 py-2 font-[JetBrains_Mono,monospace] text-xs text-gray-500 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-500">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>aid_sk_a7f3b9c2e1d4f6a8...</span>
          </div>
        </div>
      </div>
    </section>
  )
}
