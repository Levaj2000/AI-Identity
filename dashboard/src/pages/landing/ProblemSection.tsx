import { useCallback, useRef, useState, type MouseEvent } from 'react'
import { useScrollReveal } from '../../hooks/useScrollReveal'

const problems = [
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="h-6 w-6 text-red-500"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
        />
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 12.75h.008v.008H12v-.008z" />
      </svg>
    ),
    title: 'One key, total exposure',
    body: "One compromised agent means every API is exposed. A leaked key can't be scoped to just the agent that lost it.",
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="h-6 w-6 text-amber-500"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zm3 0h.008v.008H18v-.008zm-12 0h.008v.008H6v-.008z"
        />
      </svg>
    ),
    title: 'No cost attribution',
    body: "Which agent made the $400 API call? With a shared key, there's no way to trace spend back to the agent responsible.",
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
          d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
        />
      </svg>
    ),
    title: 'Audit? Good luck.',
    body: '"Which agent accessed patient data at 2:47 AM?" With shared keys, every agent looks the same in the logs.',
  },
]

/** 3D tilt card with hover glow */
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

export function ProblemSection() {
  const { ref, isVisible } = useScrollReveal()

  return (
    <section id="features" className="px-6 py-24">
      <div ref={ref} className="mx-auto max-w-6xl">
        {/* Header */}
        <div
          className={`mb-16 text-center transition-all duration-700 ease-out ${
            isVisible ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'
          }`}
        >
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-red-500/80 dark:text-red-400/80">
            The shared-key problem
          </p>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
            Most teams share one API key across all agents.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-gray-500 dark:text-slate-400">
            Here&apos;s what breaks.
          </p>
        </div>

        {/* Cards */}
        <div className="grid gap-6 md:grid-cols-3">
          {problems.map((p, i) => (
            <TiltCard key={i} index={i} isVisible={isVisible}>
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg border border-gray-200 bg-gray-50 transition-all duration-300 group-hover:scale-110 group-hover:shadow-[0_0_20px_rgba(239,68,68,0.2)] dark:border-slate-700 dark:bg-slate-800">
                {p.icon}
              </div>
              <h3 className="mb-2 text-lg font-bold text-gray-900 dark:text-white">{p.title}</h3>
              <p className="text-sm leading-relaxed text-gray-500 dark:text-slate-400">{p.body}</p>
            </TiltCard>
          ))}
        </div>
      </div>
    </section>
  )
}
