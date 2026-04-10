/**
 * EventDetailDrawer — slide-out panel showing full audit event details.
 *
 * Opens when a user clicks a timeline or table row. Shows all fields,
 * request metadata, HMAC chain info, and provides copy/export actions.
 */

import { useState } from 'react'
import type { AuditLogEntry } from '../../types/api'

// ── Helpers ──────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZoneName: 'short',
  })
}

function formatMetaValue(val: unknown): string {
  if (val == null) return 'null'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

function decisionStyle(d: string) {
  if (d === 'allow' || d === 'allowed')
    return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (d === 'deny' || d === 'denied') return 'bg-red-500/10 text-red-400 border-red-500/20'
  return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
}

function methodStyle(m: string) {
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
  event: AuditLogEntry
  onClose: () => void
  /** All events in current view, for prev/next navigation */
  events?: AuditLogEntry[]
  onNavigate?: (event: AuditLogEntry) => void
}

export function EventDetailDrawer({ event, onClose, events, onNavigate }: Props) {
  const [copied, setCopied] = useState<string | null>(null)

  // Navigation
  const currentIndex = events?.findIndex((e) => e.id === event.id) ?? -1
  const prevEvent = currentIndex > 0 ? events?.[currentIndex - 1] : undefined
  const nextEvent =
    events && currentIndex < events.length - 1 ? events[currentIndex + 1] : undefined

  // Copy helpers
  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(label)
      setTimeout(() => setCopied(null), 2000)
    } catch {
      // Fallback
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(label)
      setTimeout(() => setCopied(null), 2000)
    }
  }

  const fullJSON = JSON.stringify(event, null, 2)

  /** Build report envelope compatible with the CLI `chain` command. */
  const buildReportEnvelope = () => {
    const ts = new Date().toISOString()
    const agentShort = event.agent_id.slice(0, 8)
    const tsSlug = ts.replace(/[:.]/g, '-').slice(0, 19)
    return {
      report_id: `fr-${agentShort}-${tsSlug}`,
      generated_at: ts,
      events: [event],
      chain_verification: {
        valid: true,
        total_entries: 1,
        entries_verified: 1,
        first_broken_id: null,
        message: 'Single event export',
      },
      report_signature: null,
      stats: {
        total_events: 1,
        allowed_count: event.decision === 'allow' || event.decision === 'allowed' ? 1 : 0,
        denied_count: event.decision === 'deny' || event.decision === 'denied' ? 1 : 0,
        error_count: event.decision === 'error' ? 1 : 0,
        total_cost_usd: event.cost_estimate_usd ?? 0,
        avg_latency_ms: event.latency_ms ?? 0,
      },
    }
  }

  const exportSingleEntry = () => {
    const envelope = buildReportEnvelope()
    const blob = new Blob([JSON.stringify(envelope, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit-entry-${event.id}-${event.entry_hash.slice(0, 8)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const VERIFY_SCRIPT_URL =
    'https://raw.githubusercontent.com/Levaj2000/AI-Identity/main/cli/ai_identity_verify.py'

  const handleDownloadScript = async () => {
    try {
      const response = await fetch(VERIFY_SCRIPT_URL)
      const text = await response.text()
      const blob = new Blob([text], { type: 'text/x-python' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'ai_identity_verify.py'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      // Fallback: open in new tab if fetch fails (e.g., CORS)
      window.open(VERIFY_SCRIPT_URL, '_blank')
    }
  }

  // Extract metadata fields
  const metadata = event.request_metadata || {}
  const metaKeys = Object.keys(metadata)

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-zinc-900 border-l border-zinc-700 z-50 overflow-y-auto shadow-2xl animate-slide-in">
        {/* Header */}
        <div className="sticky top-0 bg-zinc-900/95 backdrop-blur border-b border-zinc-700 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-zinc-100">Event Detail</h2>
            <span className="text-xs font-mono text-zinc-500">#{event.entry_hash.slice(0, 8)}</span>
          </div>
          <div className="flex items-center gap-2">
            {/* Nav arrows */}
            {events && events.length > 1 && (
              <div className="flex items-center gap-1 mr-2">
                <button
                  onClick={() => prevEvent && onNavigate?.(prevEvent)}
                  disabled={!prevEvent}
                  className="p-1.5 text-zinc-400 hover:text-zinc-200 disabled:opacity-30 rounded transition-colors"
                  title="Previous event"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-4 w-4"
                  >
                    <path
                      fillRule="evenodd"
                      d="M14.77 12.79a.75.75 0 01-1.06-.02L10 8.832 6.29 12.77a.75.75 0 11-1.08-1.04l4.25-4.5a.75.75 0 011.08 0l4.25 4.5a.75.75 0 01-.02 1.06z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                <span className="text-xs text-zinc-500">
                  {currentIndex + 1}/{events.length}
                </span>
                <button
                  onClick={() => nextEvent && onNavigate?.(nextEvent)}
                  disabled={!nextEvent}
                  className="p-1.5 text-zinc-400 hover:text-zinc-200 disabled:opacity-30 rounded transition-colors"
                  title="Next event"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-4 w-4"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            )}
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
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* Decision + Method banner */}
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center rounded-md border px-3 py-1 text-sm font-semibold ${decisionStyle(event.decision)}`}
            >
              {event.decision.toUpperCase()}
            </span>
            <span
              className={`inline-flex items-center rounded px-2 py-1 text-sm font-mono font-medium ${methodStyle(event.method)}`}
            >
              {event.method}
            </span>
            <span className="text-sm font-mono text-zinc-300 truncate flex-1">
              {event.endpoint}
            </span>
          </div>

          {/* Core fields */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Event Info
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Event ID" value={String(event.id)} />
              <Field label="Timestamp" value={formatDateTime(event.created_at)} />
              <Field
                label="Agent ID"
                value={event.agent_id}
                mono
                copyable
                onCopy={() => copyToClipboard(event.agent_id, 'agent_id')}
                copied={copied === 'agent_id'}
              />
              {event.user_id && (
                <Field
                  label="User ID"
                  value={event.user_id}
                  mono
                  copyable
                  onCopy={() => copyToClipboard(event.user_id!, 'user_id')}
                  copied={copied === 'user_id'}
                />
              )}
              <Field
                label="Cost"
                value={
                  event.cost_estimate_usd != null ? `$${event.cost_estimate_usd.toFixed(6)}` : 'N/A'
                }
              />
              <Field
                label="Latency"
                value={event.latency_ms != null ? `${event.latency_ms}ms` : 'N/A'}
              />
            </div>
          </div>

          {/* Deny reason (if denied) */}
          {metadata.deny_reason != null && (
            <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4">
              <h3 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
                Deny Reason
              </h3>
              <p className="text-sm text-red-300 font-mono">{String(metadata.deny_reason)}</p>
            </div>
          )}

          {/* Request metadata */}
          {metaKeys.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                  Request Metadata
                </h3>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(metadata, null, 2), 'metadata')}
                  className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1"
                >
                  {copied === 'metadata' ? '✓ Copied' : 'Copy'}
                </button>
              </div>
              <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg overflow-hidden">
                {metaKeys.map((key) => (
                  <div
                    key={key}
                    className="flex items-start gap-3 px-4 py-2.5 border-b border-zinc-700/50 last:border-b-0"
                  >
                    <span className="text-xs font-mono text-zinc-500 shrink-0 w-32 pt-0.5">
                      {key}
                    </span>
                    <span className="text-xs font-mono text-zinc-300 break-all">
                      {formatMetaValue(metadata[key])}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* HMAC Chain */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Chain of Custody
            </h3>
            <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 space-y-3">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-zinc-500">Entry Hash</span>
                  <button
                    onClick={() => copyToClipboard(event.entry_hash, 'entry_hash')}
                    className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                  >
                    {copied === 'entry_hash' ? '✓ Copied' : 'Copy'}
                  </button>
                </div>
                <p className="text-xs font-mono text-emerald-400 break-all">{event.entry_hash}</p>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-zinc-500">Previous Hash</span>
                  <button
                    onClick={() => copyToClipboard(event.prev_hash, 'prev_hash')}
                    className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                  >
                    {copied === 'prev_hash' ? '✓ Copied' : 'Copy'}
                  </button>
                </div>
                <p className="text-xs font-mono text-zinc-400 break-all">
                  {event.prev_hash === 'GENESIS' ? (
                    <span className="text-amber-400">GENESIS (first entry in chain)</span>
                  ) : (
                    event.prev_hash
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Raw JSON */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                Raw JSON
              </h3>
              <button
                onClick={() => copyToClipboard(fullJSON, 'json')}
                className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1"
              >
                {copied === 'json' ? '✓ Copied' : 'Copy JSON'}
              </button>
            </div>
            <pre className="bg-zinc-950 border border-zinc-700 rounded-lg p-4 text-xs font-mono text-zinc-400 overflow-x-auto max-h-64 overflow-y-auto">
              {fullJSON}
            </pre>
          </div>

          {/* Actions */}
          <div className="space-y-3 pt-2 border-t border-zinc-700">
            <div className="flex items-center gap-3">
              <button
                onClick={exportSingleEntry}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-zinc-100 bg-sky-400/90 hover:bg-sky-300/90 rounded-lg transition-colors text-center"
                title="Exports in report envelope format compatible with ai_identity_verify.py"
              >
                Export Entry as JSON
              </button>
              <button
                onClick={() => copyToClipboard(fullJSON, 'json')}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors border border-zinc-600 text-center"
              >
                {copied === 'json' ? '✓ Copied!' : 'Copy to Clipboard'}
              </button>
            </div>
            <button
              onClick={handleDownloadScript}
              className="w-full px-4 py-2.5 text-sm font-medium text-emerald-100 bg-emerald-600/80 hover:bg-emerald-500/80 rounded-lg transition-colors text-center flex items-center justify-center gap-2"
            >
              Download Verify Script
            </button>
            <p className="text-xs text-zinc-500 text-center">
              Export the JSON above, then run:{' '}
              <code className="font-mono text-zinc-400">
                python3 ai_identity_verify.py chain &lt;exported-file&gt;.json
              </code>
            </p>
          </div>
        </div>
      </div>
    </>
  )
}

// ── Field subcomponent ───────────────────────────────────────────

function Field({
  label,
  value,
  mono,
  copyable,
  onCopy,
  copied,
}: {
  label: string
  value: string
  mono?: boolean
  copyable?: boolean
  onCopy?: () => void
  copied?: boolean
}) {
  return (
    <div>
      <div className="text-xs text-zinc-500 mb-0.5">{label}</div>
      <div className="flex items-center gap-1">
        <span
          className={`text-sm text-zinc-200 ${mono ? 'font-mono text-xs' : ''} truncate`}
          title={value}
        >
          {value}
        </span>
        {copyable && onCopy && (
          <button
            onClick={onCopy}
            className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors shrink-0"
            title="Copy"
          >
            {copied ? '✓' : '📋'}
          </button>
        )}
      </div>
    </div>
  )
}
