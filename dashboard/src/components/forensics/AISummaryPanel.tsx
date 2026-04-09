/**
 * AISummaryPanel — slide-out drawer showing structured AI audit summary (v2).
 *
 * Renders a Perplexity-powered structured report with dedicated sections:
 * executive summary, observed facts, assessment, recommendations,
 * risk/confidence badges, and citation sources.
 */

import type { AuditSummaryResponse } from '../../types/api'

// ── Helpers ──────────────────────────────────────────────────────

const riskBadgeStyles: Record<string, string> = {
  informational: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  low: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  high: 'bg-red-500/10 text-red-400 border-red-500/20',
}

const confidenceBadgeStyles: Record<string, string> = {
  low: 'text-zinc-500',
  medium: 'text-zinc-400',
  high: 'text-zinc-300',
}

// ── Component ────────────────────────────────────────────────────

interface Props {
  data: AuditSummaryResponse | null
  loading: boolean
  error: string | null
  onClose: () => void
  onRegenerate: () => void
}

export function AISummaryPanel({ data, loading, error, onClose, onRegenerate }: Props) {
  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-xl bg-zinc-900 border-l border-zinc-700 z-50 overflow-y-auto shadow-2xl animate-slide-in flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-zinc-900/95 backdrop-blur border-b border-zinc-700 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <span className="text-lg">✨</span>
            <h2 className="text-lg font-semibold text-zinc-100">{data?.title || 'AI Analysis'}</h2>
            {data && (
              <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded">
                {data.events_analyzed} events · {data.model_used}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-zinc-400 hover:text-zinc-200 rounded transition-colors"
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
            <div className="flex flex-col items-center justify-center py-20 text-zinc-400 gap-3">
              <div className="h-8 w-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm">Analyzing audit activity...</p>
              <p className="text-xs text-zinc-500">This usually takes 5–10 seconds</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-5 text-center">
              <p className="text-sm text-red-400 mb-3">{error}</p>
              {error.includes('Pro') ? (
                <a
                  href="/settings"
                  className="inline-flex px-4 py-2 text-sm font-medium text-zinc-100 bg-purple-500/90 hover:bg-purple-400/90 rounded-lg transition-colors"
                >
                  Upgrade Plan
                </a>
              ) : (
                <button
                  onClick={onRegenerate}
                  className="px-4 py-2 text-sm font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors border border-zinc-600"
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
                  className={`text-xs ${confidenceBadgeStyles[data.confidence] || 'text-zinc-500'}`}
                >
                  Confidence: {data.confidence}
                </span>
              </div>

              {/* Executive Summary */}
              <section>
                <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                  Executive Summary
                </h3>
                <p className="text-sm text-zinc-300 leading-relaxed">{data.executive_summary}</p>
              </section>

              {/* Observed Facts */}
              {data.observed_facts.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                    Observed Facts
                  </h3>
                  <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg overflow-hidden">
                    {data.observed_facts.map((fact, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-3 px-4 py-2.5 border-b border-zinc-700/50 last:border-b-0"
                      >
                        <span className="text-xs font-medium text-zinc-500 shrink-0 w-28 pt-0.5">
                          {fact.label}
                        </span>
                        <span className="text-xs text-zinc-300 break-words">{fact.value}</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Assessment */}
              <section>
                <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                  Assessment
                </h3>
                <div className="bg-zinc-800/30 border border-zinc-700/50 rounded-lg p-4">
                  <p className="text-sm text-zinc-300 leading-relaxed">{data.assessment}</p>
                </div>
              </section>

              {/* Recommended Follow-ups */}
              {data.recommended_follow_ups.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                    Recommended Follow-ups
                  </h3>
                  <ol className="space-y-2">
                    {data.recommended_follow_ups.map((rec, i) => (
                      <li key={i} className="flex gap-3 text-sm text-zinc-300 leading-relaxed">
                        <span className="text-xs font-semibold text-purple-400 bg-purple-500/10 rounded-full h-5 w-5 flex items-center justify-center shrink-0 mt-0.5">
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
        <div className="sticky bottom-0 bg-zinc-900/95 backdrop-blur border-t border-zinc-700 px-6 py-3 flex items-center justify-between">
          <p className="text-xs text-zinc-500">
            Generated by AI. Verify findings against raw audit data.
          </p>
          {data && !loading && (
            <button
              onClick={onRegenerate}
              className="px-3 py-1.5 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors border border-zinc-600"
            >
              Regenerate
            </button>
          )}
        </div>
      </div>
    </>
  )
}
