/**
 * ForensicsTimeline — vertical timeline of audit events.
 *
 * Renders a chronological event feed with decision badges,
 * endpoint info, cost, and latency. Deny/error events are
 * visually highlighted for quick incident identification.
 */

import { useMemo } from 'react'
import type { AuditLogEntry } from '../../types/api'
import { detectAnomalies } from './anomalyDetection'

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
      dot: 'bg-emerald-400',
      border: 'border-emerald-500/30',
      text: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
    }
  if (d === 'deny' || d === 'denied')
    return {
      dot: 'bg-red-400',
      border: 'border-red-500/30',
      text: 'text-red-400',
      bg: 'bg-red-500/10',
    }
  return {
    dot: 'bg-yellow-400',
    border: 'border-yellow-500/30',
    text: 'text-yellow-400',
    bg: 'bg-yellow-500/10',
  }
}

function methodBadge(m: string) {
  const colors: Record<string, string> = {
    GET: 'text-blue-400 bg-blue-500/10',
    POST: 'text-green-400 bg-green-500/10',
    PUT: 'text-amber-400 bg-amber-500/10',
    DELETE: 'text-red-400 bg-red-500/10',
    PATCH: 'text-purple-400 bg-purple-500/10',
  }
  return colors[m] || 'text-zinc-400 bg-zinc-500/10'
}

// ── Component ────────────────────────────────────────────────────

interface Props {
  events: AuditLogEntry[]
  onEventClick?: (event: AuditLogEntry) => void
}

export function ForensicsTimeline({ events, onEventClick }: Props) {
  const anomalyMap = useMemo(() => detectAnomalies(events), [events])

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500">
        No events in this time window.
      </div>
    )
  }

  return (
    <div className="relative pl-8">
      {/* Vertical line */}
      <div className="absolute left-3 top-0 bottom-0 w-px bg-zinc-700" />

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
          ? 'ring-1 ring-red-500/40'
          : hasLatencyOrCost
            ? 'ring-1 ring-orange-500/40'
            : ''

        return (
          <div
            key={event.id}
            className={`relative mb-4 last:mb-0 cursor-pointer transition-colors rounded-lg p-3 ${anomalyRing} ${
              isIncident
                ? 'bg-zinc-800/80 border border-red-500/20 hover:border-red-500/40'
                : 'hover:bg-zinc-800/40'
            }`}
            onClick={() => onEventClick?.(event)}
          >
            {/* Timeline dot */}
            <div
              className={`absolute -left-5 top-4 h-3 w-3 rounded-full ring-2 ring-zinc-900 ${colors.dot}`}
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
                  <span className="text-sm font-mono text-zinc-300 truncate">{event.endpoint}</span>
                </div>

                {/* Metadata row */}
                <div className="flex items-center gap-3 text-xs text-zinc-500">
                  <span>{formatTime(event.created_at)}</span>
                  {event.cost_estimate_usd != null && (
                    <span>${event.cost_estimate_usd.toFixed(4)}</span>
                  )}
                  {event.latency_ms != null && <span>{event.latency_ms}ms</span>}
                  {event.request_metadata?.deny_reason != null && (
                    <span className="text-red-400">{`${event.request_metadata.deny_reason}`}</span>
                  )}
                </div>

                {/* Anomaly pills */}
                {anomalies && anomalies.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {anomalies.map((a, i) => (
                      <span
                        key={i}
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          a.type === 'deny_cluster'
                            ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                            : 'bg-orange-500/10 text-orange-400 border border-orange-500/20'
                        }`}
                      >
                        {a.type === 'latency_spike' && '⚡ '}
                        {a.type === 'cost_outlier' && '💰 '}
                        {a.type === 'deny_cluster' && '🚨 '}
                        {a.detail}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Hash preview */}
              <div className="hidden sm:block text-xs font-mono text-zinc-600 shrink-0">
                #{event.entry_hash.slice(0, 8)}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
