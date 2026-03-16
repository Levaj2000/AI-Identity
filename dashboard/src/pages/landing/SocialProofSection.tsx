import { useScrollReveal } from '../../hooks/useScrollReveal'

const partnerSlots = [
  'Design Partner 1',
  'Design Partner 2',
  'Design Partner 3',
  'Design Partner 4',
  'Design Partner 5',
]

export function SocialProofSection() {
  const { ref, isVisible } = useScrollReveal()

  return (
    <section className="px-6 py-20">
      <div ref={ref} className="mx-auto max-w-5xl">
        <div
          className={`text-center transition-all duration-700 ease-out ${
            isVisible ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'
          }`}
        >
          <p className="mb-8 text-sm font-semibold uppercase tracking-widest text-gray-400 dark:text-slate-500">
            Trusted by forward-thinking teams
          </p>
        </div>

        {/* Partner logo placeholders */}
        <div
          className={`flex flex-wrap items-center justify-center gap-8 transition-all duration-700 ease-out sm:gap-12 ${
            isVisible ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'
          }`}
          style={{ transitionDelay: '150ms' }}
        >
          {partnerSlots.map((name, i) => (
            <div
              key={i}
              className="flex h-12 w-32 items-center justify-center rounded-lg border border-dashed border-gray-300 text-xs font-medium text-gray-400 transition-colors hover:border-indigo-300 hover:text-indigo-400 dark:border-slate-700 dark:text-slate-600 dark:hover:border-indigo-500/40 dark:hover:text-indigo-400"
            >
              {name}
            </div>
          ))}
        </div>

        {/* Design Partner CTA */}
        <div
          className={`mt-12 text-center transition-all duration-700 ease-out ${
            isVisible ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'
          }`}
          style={{ transitionDelay: '300ms' }}
        >
          <p className="mb-4 text-gray-500 dark:text-slate-400">
            Building with AI agents? Get early access and shape the product.
          </p>
          <a
            href="mailto:jeff@ai-identity.co?subject=Design%20Partner%20Interest"
            className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 px-5 py-2.5 text-sm font-semibold text-indigo-600 transition-colors hover:bg-indigo-50 dark:border-indigo-500/30 dark:text-indigo-400 dark:hover:bg-indigo-500/10"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
              <path d="M3 4a2 2 0 00-2 2v1.161l8.441 4.221a1.25 1.25 0 001.118 0L19 7.162V6a2 2 0 00-2-2H3z" />
              <path d="M19 8.839l-7.77 3.885a2.75 2.75 0 01-2.46 0L1 8.839V14a2 2 0 002 2h14a2 2 0 002-2V8.839z" />
            </svg>
            Join Design Partner Program
          </a>
        </div>
      </div>
    </section>
  )
}
