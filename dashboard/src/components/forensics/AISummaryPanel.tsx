/**
 * AISummaryPanel — slide-out drawer showing AI-generated audit summary.
 *
 * Renders a Perplexity-powered markdown summary of agent activity with
 * metadata (model used, events analysed) and a regenerate action.
 */

import Markdown from 'react-markdown'
import type { AuditSummaryResponse } from '../../types/api'

// ── Helpers ──────────────────────────────────────────────────────

/**
 * Normalize Perplexity output so section titles render as headings.
 *
 * Perplexity sometimes returns "Overview\n..." or "**Key Activity**\n..."
 * instead of "## Overview\n...". This converts known section labels into
 * proper markdown H2s for consistent rendering.
 */
function normalizeSummaryMarkdown(raw: string): string {
  const sectionLabels = [
    'Overview',
    'Key Activity',
    'Anomalies & Concerns',
    'Anomalies and Concerns',
    'Recommendations',
    'Next Steps',
  ]
  let result = raw
  for (const label of sectionLabels) {
    // Match "**Label**" or "Label" at start of line (not already a heading)
    const patterns = [
      new RegExp(`^\\*\\*${label}\\*\\*\\s*$`, 'gm'),
      new RegExp(`^${label}\\s*$`, 'gm'),
    ]
    for (const pattern of patterns) {
      result = result.replace(pattern, `## ${label}`)
    }
  }
  return result
}

/**
 * Replace `[1]`, `[2][3]` etc. with superscript links to citation URLs.
 * Falls back to plain text when a citation index has no matching URL.
 */
function injectCitationLinks(markdown: string, citations: string[]): string {
  if (!citations.length) return markdown
  // Match [N] patterns (possibly chained like [1][2])
  return markdown.replace(/\[(\d+)\]/g, (_match, numStr) => {
    const idx = parseInt(numStr, 10) - 1 // citations are 1-indexed in text
    if (idx >= 0 && idx < citations.length) {
      return `[<sup>${numStr}</sup>](${citations[idx]})`
    }
    return `<sup>${numStr}</sup>`
  })
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
            <h2 className="text-lg font-semibold text-zinc-100">AI Analysis</h2>
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
        <div className="flex-1 px-6 py-5">
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 text-zinc-400 gap-3">
              <div className="h-8 w-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm">Analyzing audit activity...</p>
              <p className="text-xs text-zinc-500">This usually takes 5–10 seconds</p>
            </div>
          )}

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

          {data && !loading && !error && (
            <div className="ai-summary-content">
              <Markdown>
                {injectCitationLinks(normalizeSummaryMarkdown(data.summary), data.citations)}
              </Markdown>
              {data.citations.length > 0 && (
                <div className="mt-6 pt-4 border-t border-zinc-700/50">
                  <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                    Sources
                  </h3>
                  <ol className="list-decimal list-inside space-y-1">
                    {data.citations.map((url, i) => (
                      <li key={i} className="text-xs text-zinc-400">
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-purple-400 hover:underline break-all"
                        >
                          {url.replace(/^https?:\/\//, '').slice(0, 80)}
                          {url.replace(/^https?:\/\//, '').length > 80 ? '...' : ''}
                        </a>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
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
