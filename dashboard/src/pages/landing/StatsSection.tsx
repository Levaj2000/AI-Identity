import { useScrollReveal } from '../../hooks/useScrollReveal'
import { useCountUp } from '../../hooks/useCountUp'

const stats = [
  { value: 50, suffix: 'K+', label: 'API calls secured', prefix: '' },
  { value: 200, suffix: '+', label: 'Agents provisioned', prefix: '' },
  { value: 99.9, suffix: '%', label: 'Uptime SLA', prefix: '', decimals: 1 },
  { value: 50, suffix: 'ms', label: 'Avg latency', prefix: '<' },
]

function StatItem({ stat, trigger }: { stat: (typeof stats)[number]; trigger: boolean }) {
  const { displayValue } = useCountUp({
    end: stat.value,
    duration: 2200,
    trigger,
    suffix: stat.suffix,
    prefix: stat.prefix,
    decimals: stat.decimals ?? 0,
  })

  return (
    <div className="flex flex-col items-center py-4">
      <span className="text-3xl font-extrabold text-indigo-600 dark:text-indigo-400 sm:text-4xl">
        {displayValue}
      </span>
      <span className="mt-1 text-sm font-medium text-gray-500 dark:text-slate-400">
        {stat.label}
      </span>
    </div>
  )
}

export function StatsSection() {
  const { ref, isVisible } = useScrollReveal(0.3)

  return (
    <section className="border-y border-gray-200 bg-gradient-to-r from-indigo-50/50 via-white to-indigo-50/50 dark:border-slate-800 dark:from-indigo-500/5 dark:via-slate-950 dark:to-indigo-500/5">
      <div
        ref={ref}
        className={`mx-auto max-w-5xl px-6 py-12 transition-all duration-700 ease-out ${
          isVisible ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'
        }`}
      >
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          {stats.map((stat, i) => (
            <StatItem key={i} stat={stat} trigger={isVisible} />
          ))}
        </div>
      </div>
    </section>
  )
}
