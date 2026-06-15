/**
 * ForensicsTimeline — vertical timeline of audit events.
 *
 * Renders a chronological event feed with decision badges,
 * endpoint info, cost, and latency. Deny/error events are
 * visually highlighted for quick incident identification.
 */

import { useMemo } from 'react'
import type { AuditLogEntry } from '../../types/api'
import { detectAnomalies, type AnomalyType } from './anomalyDetection'

// ── Helpers ──────────────────────────────────────────────────────

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function decisionColor(d: string) {
  if (d === 'allow' || d === 'allowed')
    return {
      dot: 'bg-success',
      border: 'border-success',
      text: 'text-success',
      bg: 'bg-success-soft',
    }
  if (d === 'deny' || d === 'denied')
    return {
      dot: 'bg-danger',
      border: 'border-danger',
      text: 'text-danger',
      bg: 'bg-danger-soft',
    }
  return {
    dot: 'bg-warning',
    border: 'border-warning',
    text: 'text-warning',
    bg: 'bg-warning-soft',
  }
}

function methodBadge(m: string) {
  const colors: Record<string, string> = {
    GET: 'text-brand bg-brand-soft',
    POST: 'text-success bg-success-soft',
    PUT: 'text-warning bg-warning-soft',
    DELETE: 'text-danger bg-danger-soft',
    PATCH: 'text-purple-400 bg-purple-500/10',
  }
  return colors[m] || 'text-muted bg-elevated'
}

// ── Component ────────────────────────────────────────────────────

interface Props {
  events: AuditLogEntry[]
  onEventClick?: (event: AuditLogEntry) => void
  /** Called when an analyst clicks an anomaly pill to ask the AI to explain it. */
  onExplainAnomaly?: (event: AuditLogEntry, type: AnomalyType) => void
}

export function ForensicsTimeline({ events, onEventClick, onExplainAnomaly }: Props) {
  const anomalyMap = useMemo(() => detectAnomalies(events), [events])

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-subtle">
        No events in this time window.
      </div>
    )
  }

  return (
    <div className="relative pl-8">
      {/* Vertical line */}
      <div className="absolute left-3 top-0 bottom-0 w-px bg-line" />

      {events.map((event) => {
        const colors = decisionColor(event.decision)
        const isIncident =
          event.decision === 'deny' || event.decision === 'denied' || event.decision === 'error'
        const anomalies = anomalyMap.get(event.id)
        const hasDenyCluster = anomalies?.some((a) => a.type === 'deny_cluster')
        const hasLatencyOrCost = anomalies?.some(
          (a) => a.type === 'latency_spike' || a.type === 'cost_outlier',
        )
        const anomalyRing = hasDenyCluster
          ? 'ring-1 ring-danger'
          : hasLatencyOrCost
            ? 'ring-1 ring-orange-500/40'
            : ''

        return (
          <div
            key={event.id}
            className={`relative mb-4 last:mb-0 cursor-pointer transition-colors rounded-lg p-3 ${anomalyRing} ${
              isIncident
                ? 'bg-elevated border border-danger hover:border-danger'
                : 'hover:bg-elevated'
            }`}
            onClick={() => onEventClick?.(event)}
          >
            {/* Timeline dot */}
            <div
              className={`absolute -left-5 top-4 h-3 w-3 rounded-full ring-2 ring-canvas ${colors.dot}`}
            />

            {/* Event content */}
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${colors.bg} ${colors.text} ${colors.border}`}
                  >
                    {event.decision}
                  </span>
                  <span
                    className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-mono ${methodBadge(event.method)}`}
                  >
                    {event.method}
                  </span>
                  <span className="text-sm font-mono text-muted truncate">{event.endpoint}</span>
                </div>

                {/* Metadata row */}
                <div className="flex items-center gap-3 text-xs text-subtle">
                  <span>{formatTime(event.created_at)}</span>
                  {event.cost_estimate_usd != null && (
                    <span>${event.cost_estimate_usd.toFixed(4)}</span>
                  )}
                  {event.latency_ms != null && <span>{event.latency_ms}ms</span>}
                  {event.request_metadata?.deny_reason != null && (
                    <span className="text-danger">{`${event.request_metadata.deny_reason}`}</span>
                  )}
                </div>

                {/* Anomaly pills */}
                {anomalies && anomalies.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {anomalies.map((a, i) => {
                      const baseClasses = `inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                        a.type === 'deny_cluster'
                          ? 'bg-danger-soft text-danger border border-danger'
                          : 'bg-orange-500/10 text-orange-400 border border-orange-500/20'
                      }`
                      const icon =
                        a.type === 'latency_spike'
                          ? '⚡ '
                          : a.type === 'cost_outlier'
                            ? '💰 '
                            : '🚨 '

                      if (!onExplainAnomaly) {
                        return (
                          <span key={i} className={baseClasses}>
                            {icon}
                            {a.detail}
                          </span>
                        )
                      }

                      return (
                        <button
                          key={i}
                          type="button"
                          onClick={(ev) => {
                            ev.stopPropagation()
                            onExplainAnomaly(event, a.type)
                          }}
                          className={`${baseClasses} hover:brightness-125 hover:border-current transition-all cursor-pointer`}
                          title={`Ask AI to explain this ${a.type.replace('_', ' ')}`}
                        >
                          {icon}
                          {a.detail}
                          <span className="ml-1 opacity-70">✨ Explain</span>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Hash preview */}
              <div className="hidden sm:block text-xs font-mono text-faint shrink-0">
                #{event.entry_hash.slice(0, 8)}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
