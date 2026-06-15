/**
 * AISummaryPanel — slide-out drawer showing structured AI audit summary (v2).
 *
 * Renders a Perplexity-powered structured report with dedicated sections:
 * executive summary, observed facts, assessment, recommendations,
 * risk/confidence badges, and citation sources.
 *
 * Numeric facts (total/allowed/denied/errors/time window) are rendered
 * directly from the deterministic `facts` field — never from the LLM
 * prose. This guarantees the AI panel cannot disagree with the KPI bar.
 */

import type { AuditSummaryResponse, ObservedFact, SummaryFacts } from '../../types/api'

// ── Helpers ──────────────────────────────────────────────────────

const riskBadgeStyles: Record<string, string> = {
  informational: 'bg-elevated text-muted border-line',
  low: 'bg-brand-soft text-brand border-brand',
  medium: 'bg-warning-soft text-warning border-warning',
  high: 'bg-danger-soft text-danger border-danger',
}

const confidenceBadgeStyles: Record<string, string> = {
  low: 'text-subtle',
  medium: 'text-muted',
  high: 'text-muted',
}

/**
 * Build the Observed Facts rows from the deterministic `facts` field.
 * This is the *only* source of truth for the numeric rows in the panel —
 * any rows the LLM may have produced in `observed_facts` are ignored.
 */
function buildDeterministicFacts(facts: SummaryFacts | null | undefined): ObservedFact[] {
  if (!facts) return []
  const fmtCount = (n: number | null): string => (n == null ? 'not available' : String(n))
  const fmtWindow = (start: string | null, end: string | null): string => {
    if (start == null && end == null) return 'not available'
    if (start != null && end != null && start === end) return start
    return `${start ?? 'unbounded'} → ${end ?? 'unbounded'}`
  }
  return [
    { label: 'Time window', value: fmtWindow(facts.time_window_start, facts.time_window_end) },
    { label: 'Total requests', value: fmtCount(facts.total_requests) },
    { label: 'Requests allowed', value: fmtCount(facts.requests_allowed) },
    { label: 'Requests denied', value: fmtCount(facts.requests_denied) },
    { label: 'Errors', value: fmtCount(facts.errors) },
  ]
}

// ── Component ────────────────────────────────────────────────────

interface Props {
  data: AuditSummaryResponse | null
  loading: boolean
  error: string | null
  /** Human-readable description of what's being analyzed (e.g. "Analyzing 55 visible events"). */
  scopeLabel?: string
  onClose: () => void
  onRegenerate: () => void
}

export function AISummaryPanel({ data, loading, error, scopeLabel, onClose, onRegenerate }: Props) {
  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-xl bg-surface border-l border-line z-50 overflow-y-auto shadow-2xl animate-slide-in flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-surface/95 backdrop-blur border-b border-line px-6 py-4 flex items-start justify-between z-10">
          <div className="flex items-start gap-3 min-w-0">
            <span className="text-lg leading-6">✨</span>
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-ink truncate">
                {data?.title || 'AI Analysis'}
              </h2>
              {scopeLabel && (
                <p className="text-xs text-ai mt-0.5 truncate" title={scopeLabel}>
                  {scopeLabel}
                </p>
              )}
              {data && (
                <span className="inline-block mt-1.5 text-xs text-subtle bg-elevated px-2 py-0.5 rounded">
                  {data.events_analyzed} event{data.events_analyzed === 1 ? '' : 's'} ·{' '}
                  {data.model_used}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-muted hover:text-ink rounded transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5"
            >
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 px-6 py-5 space-y-6">
          {/* Loading */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 text-muted gap-3">
              <div className="h-8 w-8 border-2 border-ai border-t-transparent rounded-full animate-spin" />
              <p className="text-sm">Analyzing audit activity...</p>
              <p className="text-xs text-subtle">This usually takes 5–10 seconds</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-danger-soft border border-danger rounded-lg p-5 text-center">
              <p className="text-sm text-danger mb-3">{error}</p>
              {error.includes('Pro') ? (
                <a
                  href="/settings"
                  className="inline-flex px-4 py-2 text-sm font-medium bg-ai text-ai-ink hover:opacity-90 rounded-lg transition-colors"
                >
                  Upgrade Plan
                </a>
              ) : (
                <button
                  onClick={onRegenerate}
                  className="px-4 py-2 text-sm font-medium text-muted bg-elevated hover:bg-elevated rounded-lg transition-colors border border-line-strong"
                >
                  Try Again
                </button>
              )}
            </div>
          )}

          {/* Structured Report */}
          {data && !loading && !error && (
            <>
              {/* Risk + Confidence badges */}
              <div className="flex items-center gap-3">
                <span
                  className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-semibold uppercase tracking-wider ${riskBadgeStyles[data.risk_level] || riskBadgeStyles.informational}`}
                >
                  {data.risk_level}
                </span>
                <span
                  className={`text-xs ${confidenceBadgeStyles[data.confidence] || 'text-subtle'}`}
                >
                  Confidence: {data.confidence}
                </span>
              </div>

              {/* Executive Summary */}
              <section>
                <h3 className="text-xs font-semibold text-subtle uppercase tracking-wider mb-2">
                  Executive Summary
                </h3>
                <p className="text-sm text-muted leading-relaxed">{data.executive_summary}</p>
              </section>

              {/* Observed Facts — rendered from deterministic `facts` only.
                   The LLM has no input here, so these numbers always match
                   the KPI bar. */}
              {(() => {
                const factRows = buildDeterministicFacts(data.facts)
                if (factRows.length === 0) return null
                return (
                  <section>
                    <h3 className="text-xs font-semibold text-subtle uppercase tracking-wider mb-2">
                      Observed Facts
                    </h3>
                    <div className="bg-inset border border-line rounded-lg overflow-hidden">
                      {factRows.map((fact, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-3 px-4 py-2.5 border-b border-line last:border-b-0"
                        >
                          <span className="text-xs font-medium text-subtle shrink-0 w-28 pt-0.5">
                            {fact.label}
                          </span>
                          <span className="text-xs text-muted break-words">{fact.value}</span>
                        </div>
                      ))}
                    </div>
                    {data.facts?.aggregate_window_source === 'event_neighborhood' && (
                      <p className="text-xs text-subtle mt-2 italic">
                        Counts are taken from a ±24h window around the selected event.
                      </p>
                    )}
                    {data.facts?.aggregate_window_source === 'unavailable' && (
                      <p className="text-xs text-subtle mt-2 italic">
                        No aggregate window applies to this scope, so totals are unavailable.
                      </p>
                    )}
                  </section>
                )
              })()}

              {/* Assessment */}
              <section>
                <h3 className="text-xs font-semibold text-subtle uppercase tracking-wider mb-2">
                  Assessment
                </h3>
                <div className="bg-inset border border-line rounded-lg p-4">
                  <p className="text-sm text-muted leading-relaxed">{data.assessment}</p>
                </div>
              </section>

              {/* Recommended Follow-ups */}
              {data.recommended_follow_ups.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-subtle uppercase tracking-wider mb-2">
                    Recommended Follow-ups
                  </h3>
                  <ol className="space-y-2">
                    {data.recommended_follow_ups.map((rec, i) => (
                      <li key={i} className="flex gap-3 text-sm text-muted leading-relaxed">
                        <span className="text-xs font-semibold text-ai bg-ai-soft rounded-full h-5 w-5 flex items-center justify-center shrink-0 mt-0.5">
                          {i + 1}
                        </span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ol>
                </section>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-surface/95 backdrop-blur border-t border-line px-6 py-3 flex items-center justify-between">
          <p className="text-xs text-subtle">
            AI-generated analysis based on AI Identity audit data. Treat as an aid to investigation
            and confirm against source logs.
          </p>
          {data && !loading && (
            <button
              onClick={onRegenerate}
              className="px-3 py-1.5 text-xs font-medium text-muted bg-elevated hover:bg-elevated rounded-lg transition-colors border border-line-strong"
            >
              Regenerate
            </button>
          )}
        </div>
      </div>
    </>
  )
}
