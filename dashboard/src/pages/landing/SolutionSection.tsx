import { useCallback, useRef, useState, type MouseEvent } from 'react'
import { useScrollReveal } from '../../hooks/useScrollReveal'

const solutions = [
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="h-6 w-6 text-indigo-500"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z"
        />
      </svg>
    ),
    title: 'Per-agent API keys',
    body: 'Every agent gets its own cryptographic identity — aid_sk_… keys scoped to exactly one agent. Revoke one without touching the rest.',
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="h-6 w-6 text-indigo-500"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
        />
      </svg>
    ),
    title: 'Scoped permissions',
    body: 'Define what each agent can access — which APIs, which endpoints, what rate limits. Least-privilege by default.',
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="h-6 w-6 text-indigo-500"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z"
        />
      </svg>
    ),
    title: 'Signed audit trail',
    body: 'HMAC-chained logs plus DSSE-signed session attestations (ECDSA P-256, KMS-held keys). Auditors verify offline — no vendor trust required.',
  },
]

/** 3D tilt card with indigo glow */
function TiltCard({
  children,
  index,
  isVisible,
}: {
  children: React.ReactNode
  index: number
  isVisible: boolean
}) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [tilt, setTilt] = useState({ rotateX: 0, rotateY: 0 })
  const [isHovered, setIsHovered] = useState(false)
  const rafId = useRef(0)

  const handleMouseMove = useCallback((e: MouseEvent<HTMLDivElement>) => {
    const el = cardRef.current
    if (!el) return

    if (rafId.current) cancelAnimationFrame(rafId.current)
    rafId.current = requestAnimationFrame(() => {
      const rect = el.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width - 0.5
      const y = (e.clientY - rect.top) / rect.height - 0.5
      setTilt({ rotateX: -y * 16, rotateY: x * 16 })
    })
  }, [])

  const handleMouseLeave = useCallback(() => {
    if (rafId.current) cancelAnimationFrame(rafId.current)
    setTilt({ rotateX: 0, rotateY: 0 })
    setIsHovered(false)
  }, [])

  return (
    <div className="perspective-container">
      <div
        ref={cardRef}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={handleMouseLeave}
        className={`card-glow group rounded-xl border border-gray-200 bg-white p-8 transition-all duration-500 ease-out dark:border-slate-800 dark:bg-slate-900/50 ${
          isVisible ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
        }`}
        style={{
          transitionDelay: `${150 + index * 100}ms`,
          transform: `perspective(800px) rotateX(${tilt.rotateX}deg) rotateY(${tilt.rotateY}deg) ${isVisible ? 'translateY(0)' : 'translateY(32px)'}`,
          willChange: isHovered ? 'transform' : 'auto',
        }}
      >
        {children}
      </div>
    </div>
  )
}

export function SolutionSection() {
  const { ref, isVisible } = useScrollReveal()

  return (
    <section className="bg-gray-50 px-6 py-24 dark:bg-slate-900/30">
      <div ref={ref} className="mx-auto max-w-6xl">
        {/* Header */}
        <div
          className={`mb-16 text-center transition-all duration-700 ease-out ${
            isVisible ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'
          }`}
        >
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-indigo-500/80 dark:text-indigo-400/80">
            Built for agents
          </p>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
            One identity per agent. Zero shared secrets.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-gray-500 dark:text-slate-400">
            AI Identity gives every agent a verifiable identity, context-aware policy on agent
            metadata, and a cryptographically-signed audit trail auditors can verify offline.
          </p>
        </div>

        {/* Cards */}
        <div className="grid gap-6 md:grid-cols-3">
          {solutions.map((s, i) => (
            <TiltCard key={i} index={i} isVisible={isVisible}>
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg border border-indigo-100 bg-indigo-50 transition-all duration-300 group-hover:scale-110 group-hover:shadow-[0_0_20px_rgba(99,102,241,0.3)] dark:border-indigo-500/20 dark:bg-indigo-500/10">
                {s.icon}
              </div>
              <h3 className="mb-2 text-lg font-bold text-gray-900 dark:text-white">{s.title}</h3>
              <p className="text-sm leading-relaxed text-gray-500 dark:text-slate-400">{s.body}</p>
            </TiltCard>
          ))}
        </div>
      </div>
    </section>
  )
}
