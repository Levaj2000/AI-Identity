import { Link } from 'react-router-dom'
import { useScrollReveal } from '../../hooks/useScrollReveal'

const orbs = [
  {
    size: 280,
    top: '-15%',
    right: '-8%',
    animation: 'float-orb-1',
    duration: '20s',
    opacity: 0.08,
  },
  {
    size: 200,
    bottom: '-10%',
    left: '-5%',
    animation: 'float-orb-2',
    duration: '25s',
    opacity: 0.06,
  },
  { size: 160, top: '30%', right: '20%', animation: 'float-orb-3', duration: '22s', opacity: 0.1 },
  {
    size: 120,
    bottom: '20%',
    left: '25%',
    animation: 'float-orb-1',
    duration: '18s',
    opacity: 0.05,
  },
  { size: 100, top: '10%', left: '15%', animation: 'float-orb-2', duration: '23s', opacity: 0.07 },
]

export function CTASection() {
  const { ref, isVisible } = useScrollReveal()

  return (
    <section className="px-6 py-24">
      <div ref={ref} className="mx-auto max-w-4xl">
        <div
          className={`relative overflow-hidden rounded-2xl p-12 text-center shadow-2xl transition-all duration-700 ease-out sm:p-16 ${
            isVisible ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
          }`}
          style={{
            background:
              'linear-gradient(135deg, #4f46e5 0%, #4338ca 30%, #3730a3 60%, #312e81 100%)',
            backgroundSize: '300% 300%',
            animation: 'gradient-shift 8s ease infinite',
          }}
        >
          {/* Floating orbs */}
          <div className="pointer-events-none absolute inset-0 overflow-hidden">
            {orbs.map((orb, i) => (
              <div
                key={i}
                className="absolute rounded-full bg-white"
                style={{
                  width: orb.size,
                  height: orb.size,
                  top: orb.top,
                  right: orb.right,
                  bottom: orb.bottom,
                  left: orb.left,
                  opacity: orb.opacity,
                  animation: `${orb.animation} ${orb.duration} ease-in-out infinite`,
                }}
              />
            ))}
          </div>

          <div className="relative">
            <h2 className="text-3xl font-bold text-white sm:text-4xl">
              Ready to give your agents an identity?
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-indigo-200">
              Set up in minutes. Free while in beta. No credit card required.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link
                to="/app"
                className="group inline-flex items-center gap-2 rounded-lg bg-white px-8 py-3.5 text-sm font-bold text-indigo-700 shadow-lg transition-all duration-200 hover:scale-[1.03] hover:shadow-[0_8px_30px_rgba(255,255,255,0.3)] active:scale-[0.98]"
              >
                Get Started Free
                <svg
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                >
                  <path
                    fillRule="evenodd"
                    d="M3 10a.75.75 0 01.75-.75h10.638l-3.96-4.158a.75.75 0 111.08-1.04l5.25 5.5a.75.75 0 010 1.08l-5.25 5.5a.75.75 0 11-1.08-1.04l3.96-4.158H3.75A.75.75 0 013 10z"
                    clipRule="evenodd"
                  />
                </svg>
              </Link>
              <a
                href="https://ai-identity-api.onrender.com/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-white/30 px-8 py-3.5 text-sm font-semibold text-white transition-all duration-200 hover:scale-[1.02] hover:bg-white/10 active:scale-[0.98]"
              >
                Read the Docs
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
