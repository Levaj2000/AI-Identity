import { useState, useEffect } from 'react'
import { apiFetch, toQueryString } from '../services/api/client'
import type { AuditLogEntry } from '../types/api'
import { EventDetailDrawer } from '../components/forensics/EventDetailDrawer'
import { fetchAuditStats, verifyAuditChain } from '../services/api/forensics'

// ── Types ────────────────────────────────────────────────────────

interface AuditListResponse {
  items: AuditLogEntry[]
  total: number
  limit: number
  offset: number
}

interface VerifyResponse {
  valid: boolean
  total_entries: number
  entries_verified: number
  first_broken_id: number | null
  message: string
}

// ── Helpers ──────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/** Match both "allow"/"allowed" and "deny"/"denied" variants (same as Forensics page). */
function decisionBadge(d: string) {
  if (d === 'allow' || d === 'allowed') return 'bg-success-soft text-success border-success'
  if (d === 'deny' || d === 'denied') return 'bg-danger-soft text-danger border-danger'
  return 'bg-warning-soft text-warning border-warning'
}

/** Check if a decision string represents a deny. */
function isDenyDecision(d: string) {
  return d === 'deny' || d === 'denied'
}

/** Check if a decision string represents an allow. */
function isAllowDecision(d: string) {
  return d === 'allow' || d === 'allowed'
}

// ── Component ────────────────────────────────────────────────────

export function CompliancePage() {
  // Audit log state
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const limit = 20

  // Filters
  const [filterDecision, setFilterDecision] = useState<string>('')
  const [filterAgent, setFilterAgent] = useState<string>('')

  // Chain verification
  const [verifyResult, setVerifyResult] = useState<VerifyResponse | null>(null)
  const [verifying, setVerifying] = useState(false)
  const [lastVerified, setLastVerified] = useState<string | null>(null)

  // Stats
  const [stats, setStats] = useState({
    totalEntries: 0,
    allowCount: 0,
    denyCount: 0,
    errorCount: 0,
  })

  // Event detail drawer
  const [selectedEvent, setSelectedEvent] = useState<AuditLogEntry | null>(null)

  // ── Fetch audit entries ──────────────────────────────────────

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const qs = toQueryString({
          limit,
          offset,
          decision: filterDecision || undefined,
          agent_id: filterAgent || undefined,
        })
        const data = await apiFetch<AuditListResponse>(`/api/v1/audit${qs}`)
        if (!cancelled) {
          setEntries(data.items)
          setTotal(data.total)
        }
      } catch {
        if (!cancelled) {
          setEntries([])
          setTotal(0)
        }
      }
      if (!cancelled) setLoading(false)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [offset, filterDecision, filterAgent])

  // ── Fetch stats on mount ─────────────────────────────────────
  // Single aggregate call — /audit/stats already sums the "allow"/"allowed"
  // and "deny"/"denied" variants server-side, so no per-decision probes.

  useEffect(() => {
    async function loadStats() {
      try {
        const s = await fetchAuditStats({})
        setStats({
          totalEntries: s.total_events,
          allowCount: s.allowed_count,
          denyCount: s.denied_count,
          errorCount: s.error_count,
        })
      } catch {
        // Stats failed — non-critical
      }
    }
    loadStats()
  }, [])

  // ── Verify chain (uses shared forensics API) ──────────────────

  const runVerify = async () => {
    setVerifying(true)
    try {
      const data = await verifyAuditChain(filterAgent || undefined)
      setVerifyResult(data)
      setLastVerified(new Date().toLocaleString())
    } catch {
      setVerifyResult({
        valid: false,
        total_entries: 0,
        entries_verified: 0,
        first_broken_id: null,
        message: 'Verification request failed',
      })
    }
    setVerifying(false)
  }

  // ── Auto-verify on mount ──────────────────────────────────────

  useEffect(() => {
    runVerify()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Export CSV ────────────────────────────────────────────────

  const exportCSV = async () => {
    try {
      const qs = toQueryString({
        limit: 500,
        offset: 0,
        decision: filterDecision || undefined,
        agent_id: filterAgent || undefined,
      })
      const data = await apiFetch<AuditListResponse>(`/api/v1/audit${qs}`)

      const headers = [
        'id',
        'created_at',
        'agent_id',
        'endpoint',
        'method',
        'decision',
        'cost_estimate_usd',
        'latency_ms',
        'entry_hash',
        'prev_hash',
        'deny_reason',
      ]
      const rows = data.items.map((e) =>
        [
          e.id,
          e.created_at,
          e.agent_id,
          e.endpoint,
          e.method,
          e.decision,
          e.cost_estimate_usd ?? '',
          e.latency_ms ?? '',
          e.entry_hash,
          e.prev_hash,
          (e.request_metadata?.deny_reason as string) ?? '',
        ].join(','),
      )

      const csv = [headers.join(','), ...rows].join('\n')
      const blob = new Blob([csv], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ai-identity-audit-log-${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // Export failed
    }
  }

  // ── Export JSON ───────────────────────────────────────────────

  const exportJSON = async () => {
    try {
      const qs = toQueryString({
        limit: 500,
        offset: 0,
        decision: filterDecision || undefined,
        agent_id: filterAgent || undefined,
      })
      const data = await apiFetch<AuditListResponse>(`/api/v1/audit${qs}`)

      const blob = new Blob([JSON.stringify(data.items, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ai-identity-audit-log-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // Export failed
    }
  }

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Compliance & Audit</h1>
          <p className="mt-1 text-sm text-subtle">
            SOC 2-ready audit trail — HMAC-SHA256 integrity chain plus DSSE + ECDSA P-256 session
            attestations auditors can verify offline
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportCSV}
            className="rounded-lg border border-line bg-surface px-3 py-2 text-sm text-muted hover:border-brand hover:text-ink transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              CSV
            </span>
          </button>
          <button
            onClick={exportJSON}
            className="rounded-lg border border-line bg-surface px-3 py-2 text-sm text-muted hover:border-brand hover:text-ink transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              JSON
            </span>
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Chain Integrity */}
        <div className="rounded-xl border border-line bg-surface p-5">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-subtle">
              Chain Integrity
            </p>
            <div
              className={`h-3 w-3 rounded-full ${
                verifyResult === null
                  ? 'bg-faint'
                  : verifyResult.valid
                    ? 'bg-success shadow-[0_0_8px_rgba(52,211,153,0.5)]'
                    : 'bg-danger shadow-[0_0_8px_rgba(248,113,113,0.5)]'
              }`}
            />
          </div>
          <p className="mt-2 text-2xl font-bold text-ink">
            {verifyResult === null
              ? verifying
                ? 'Checking...'
                : '---'
              : verifyResult.valid
                ? 'VALID'
                : 'BROKEN'}
          </p>
          <p className="mt-1 text-xs text-subtle">
            {lastVerified
              ? `Last checked ${lastVerified}`
              : verifying
                ? 'Verifying chain...'
                : 'Not yet verified'}
          </p>
          <button
            onClick={runVerify}
            disabled={verifying}
            className="mt-3 w-full rounded-lg bg-brand-soft px-3 py-1.5 text-xs font-medium text-brand hover:bg-brand-soft transition-colors disabled:opacity-50"
          >
            {verifying ? 'Verifying...' : 'Verify Now'}
          </button>
        </div>

        {/* Total Entries */}
        <div className="rounded-xl border border-line bg-surface p-5">
          <p className="text-xs font-medium uppercase tracking-wider text-subtle">Total Entries</p>
          <p className="mt-2 text-2xl font-bold text-ink">{stats.totalEntries.toLocaleString()}</p>
          <p className="mt-1 text-xs text-subtle">Append-only audit records</p>
        </div>

        {/* Allow / Deny */}
        <div className="rounded-xl border border-line bg-surface p-5">
          <p className="text-xs font-medium uppercase tracking-wider text-subtle">Decisions</p>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="text-2xl font-bold text-success">{stats.allowCount}</span>
            <span className="text-sm text-subtle">allowed</span>
          </div>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="text-lg font-bold text-danger">{stats.denyCount}</span>
            <span className="text-sm text-subtle">denied</span>
            {stats.errorCount > 0 && (
              <>
                <span className="text-lg font-bold text-warning">{stats.errorCount}</span>
                <span className="text-sm text-subtle">errors</span>
              </>
            )}
          </div>
        </div>

        {/* Compliance Score */}
        <div className="rounded-xl border border-line bg-surface p-5">
          <p className="text-xs font-medium uppercase tracking-wider text-subtle">
            Compliance Readiness
          </p>
          <p className="mt-2 text-2xl font-bold text-brand">SOC 2</p>
          <div className="mt-2 space-y-1">
            <div className="flex items-center gap-2 text-xs">
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span className="text-muted">HMAC integrity chain</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span className="text-muted">Append-only enforcement</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span className="text-muted">PII sanitization</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span className="text-muted">Tenant isolation (RLS)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Verification detail banner */}
      {verifyResult && (
        <div
          className={`rounded-xl border p-4 ${
            verifyResult.valid ? 'border-success bg-success-soft' : 'border-danger bg-danger-soft'
          }`}
        >
          <div className="flex items-start gap-3">
            <div
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                verifyResult.valid ? 'bg-success-soft' : 'bg-danger-soft'
              }`}
            >
              {verifyResult.valid ? (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2.5"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#f87171"
                  strokeWidth="2.5"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              )}
            </div>
            <div>
              <p
                className={`text-sm font-medium ${verifyResult.valid ? 'text-success' : 'text-danger'}`}
              >
                {verifyResult.message}
              </p>
              <p className="mt-0.5 text-xs text-subtle">
                {verifyResult.entries_verified} of {verifyResult.total_entries} entries verified via
                HMAC-SHA256 chain
                {verifyResult.first_broken_id &&
                  ` — first break at entry #${verifyResult.first_broken_id}`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={filterDecision}
          onChange={(e) => {
            setFilterDecision(e.target.value)
            setOffset(0)
          }}
          className="rounded-lg border border-line bg-surface px-3 py-2 text-sm text-muted focus:border-brand focus:outline-none"
        >
          <option value="">All decisions</option>
          <option value="allowed">Allowed</option>
          <option value="denied">Denied</option>
          <option value="error">Error</option>
        </select>

        <input
          type="text"
          placeholder="Filter by agent ID..."
          value={filterAgent}
          onChange={(e) => {
            setFilterAgent(e.target.value)
            setOffset(0)
          }}
          className="rounded-lg border border-line bg-surface px-3 py-2 text-sm text-muted placeholder:text-faint focus:border-brand focus:outline-none"
        />

        <span className="text-xs text-subtle">
          {total} {total === 1 ? 'entry' : 'entries'}
        </span>
      </div>

      {/* Audit log table */}
      <div className="overflow-hidden rounded-xl border border-line">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-elevated">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  #
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Timestamp
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Agent
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Endpoint
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Method
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Decision
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Details
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Hash
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-subtle">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-2 w-2 animate-bounce rounded-full bg-brand" />
                      <div
                        className="h-2 w-2 animate-bounce rounded-full bg-brand"
                        style={{ animationDelay: '0.15s' }}
                      />
                      <div
                        className="h-2 w-2 animate-bounce rounded-full bg-brand"
                        style={{ animationDelay: '0.3s' }}
                      />
                    </div>
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-subtle">
                    <p className="text-sm">No audit entries found</p>
                    <p className="mt-1 text-xs">
                      Entries are created when agents make requests through the gateway
                    </p>
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr
                    key={entry.id}
                    className="bg-surface hover:bg-elevated transition-colors cursor-pointer"
                    onClick={() => setSelectedEvent(entry)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-subtle">{entry.id}</td>
                    <td className="px-4 py-3 text-xs text-muted whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-muted">
                      {entry.agent_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-ink">{entry.endpoint}</td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-muted">
                        {entry.method}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${decisionBadge(entry.decision)}`}
                      >
                        {entry.decision}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-subtle max-w-[200px] truncate">
                      {entry.request_metadata?.deny_reason
                        ? String(entry.request_metadata.deny_reason)
                        : entry.latency_ms
                          ? `${entry.latency_ms}ms`
                          : '---'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="font-mono text-xs text-faint cursor-help"
                        title={`entry: ${entry.entry_hash}\nprev: ${entry.prev_hash}`}
                      >
                        {entry.entry_hash.slice(0, 12)}...
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-line bg-elevated px-4 py-3">
            <p className="text-xs text-subtle">
              Page {currentPage} of {totalPages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="rounded-lg border border-line px-3 py-1.5 text-xs text-muted hover:text-ink disabled:opacity-30 transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="rounded-lg border border-line px-3 py-1.5 text-xs text-muted hover:text-ink disabled:opacity-30 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Hash chain visualization */}
      {entries.length > 0 && (
        <div className="rounded-xl border border-line bg-surface p-5">
          <h3 className="text-sm font-medium text-ink">HMAC Chain Visualization</h3>
          <p className="mt-1 text-xs text-subtle">
            Each entry's hash includes the previous entry's hash, creating a tamper-evident chain
          </p>
          <div className="mt-4 flex items-center gap-2 overflow-x-auto pb-2">
            {entries.slice(0, 8).map((entry, i) => (
              <div key={entry.id} className="flex items-center gap-2 shrink-0">
                <div
                  className={`rounded-lg border px-3 py-2 text-center cursor-pointer hover:opacity-80 transition-opacity ${
                    isAllowDecision(entry.decision)
                      ? 'border-success bg-success-soft'
                      : isDenyDecision(entry.decision)
                        ? 'border-danger bg-danger-soft'
                        : 'border-warning bg-warning-soft'
                  }`}
                  onClick={() => setSelectedEvent(entry)}
                >
                  <p className="font-mono text-[10px] text-subtle">#{entry.id}</p>
                  <p
                    className={`text-xs font-medium ${
                      isAllowDecision(entry.decision)
                        ? 'text-success'
                        : isDenyDecision(entry.decision)
                          ? 'text-danger'
                          : 'text-warning'
                    }`}
                  >
                    {entry.decision}
                  </p>
                  <p className="mt-0.5 font-mono text-[9px] text-faint">
                    {entry.entry_hash.slice(0, 8)}
                  </p>
                </div>
                {i < Math.min(entries.length, 8) - 1 && (
                  <svg width="20" height="12" viewBox="0 0 20 12" className="text-brand shrink-0">
                    <line x1="0" y1="6" x2="14" y2="6" stroke="currentColor" strokeWidth="1.5" />
                    <polyline
                      points="11,2 15,6 11,10"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    />
                  </svg>
                )}
              </div>
            ))}
            {entries.length > 8 && (
              <span className="text-xs text-subtle shrink-0">+{entries.length - 8} more</span>
            )}
          </div>
        </div>
      )}

      {/* Event Detail Drawer (reused from Forensics page) */}
      {selectedEvent && (
        <EventDetailDrawer
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          events={entries}
          onNavigate={setSelectedEvent}
        />
      )}
    </div>
  )
}
