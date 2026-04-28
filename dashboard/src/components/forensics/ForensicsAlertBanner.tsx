/**
 * ForensicsAlertBanner — proactively surface high-signal anomalies on the
 * Forensics page, with one-click CTAs into the AI Forensics flow.
 *
 * The page computes a list of alerts from `detectAnomalies()` + chain status
 * and passes them in. Each alert renders as a row with severity styling, a
 * description, a primary CTA (e.g. "Investigate cluster"), and a dismiss
 * button. Dismissal is per-fingerprint and persists in sessionStorage — so
 * navigating away and back does not re-prompt for the same anomaly, but a
 * fresh anomaly (different fingerprint) re-triggers.
 */

export type AlertSeverity = 'high' | 'medium'

export interface ForensicsAlert {
  /** Stable hash of (category, count, anchor timestamp). Used for dismissal. */
  fingerprint: string
  severity: AlertSeverity
  icon: string
  title: string
  description: string
  ctaLabel: string
  onCTA: () => void
}

interface Props {
  alerts: ForensicsAlert[]
  onDismiss: (fingerprint: string) => void
}

const severityStyles: Record<AlertSeverity, string> = {
  high: 'border-red-500/30 bg-red-500/5',
  medium: 'border-orange-500/30 bg-orange-500/5',
}

const severityIconBg: Record<AlertSeverity, string> = {
  high: 'bg-red-500/15 text-red-400',
  medium: 'bg-orange-500/15 text-orange-400',
}

const severityCta: Record<AlertSeverity, string> = {
  high: 'bg-red-500/90 hover:bg-red-400/90 text-zinc-100',
  medium: 'bg-orange-500/90 hover:bg-orange-400/90 text-zinc-100',
}

export function ForensicsAlertBanner({ alerts, onDismiss }: Props) {
  if (alerts.length === 0) return null

  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <div
          key={alert.fingerprint}
          className={`flex items-start justify-between gap-3 rounded-xl border px-4 py-3 ${severityStyles[alert.severity]}`}
        >
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <span
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm ${severityIconBg[alert.severity]}`}
              aria-hidden="true"
            >
              {alert.icon}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-zinc-100">{alert.title}</p>
              <p className="text-xs text-zinc-400 mt-0.5">{alert.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={alert.onCTA}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${severityCta[alert.severity]}`}
            >
              {alert.ctaLabel}
            </button>
            <button
              onClick={() => onDismiss(alert.fingerprint)}
              title="Dismiss for this session"
              className="p-1.5 text-zinc-500 hover:text-zinc-300 transition-colors"
              aria-label="Dismiss alert"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
