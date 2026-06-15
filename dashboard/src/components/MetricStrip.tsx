import type { DashboardStats } from '../types/api'

interface MetricStripProps {
  stats: DashboardStats
}

const METRICS: { key: keyof DashboardStats; label: string; tone: string }[] = [
  { key: 'totalAgents', label: 'Total', tone: 'text-ink' },
  { key: 'activeAgents', label: 'Active', tone: 'text-success' },
  { key: 'suspendedAgents', label: 'Suspended', tone: 'text-warning' },
  { key: 'revokedAgents', label: 'Revoked', tone: 'text-danger' },
]

/** Compact, divided metric strip — the demoted, at-a-glance counts. */
export function MetricStrip({ stats }: MetricStripProps) {
  return (
    <div className="flex items-center rounded-xl border border-line bg-surface px-2 py-3">
      {METRICS.map((m, i) => (
        <div key={m.key} className="flex flex-1 items-center">
          {i > 0 && <div className="h-7 w-px shrink-0 bg-line" />}
          <div className="flex-1 px-2 text-center">
            <div
              className={`text-xl font-medium ${m.tone}`}
              style={{ fontVariantNumeric: 'tabular-nums' }}
            >
              {stats[m.key]}
            </div>
            <div className="mt-0.5 text-[11px] uppercase tracking-wider text-subtle">{m.label}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
