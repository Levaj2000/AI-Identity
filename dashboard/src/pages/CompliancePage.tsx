import { useState, useEffect } from 'react'
import { apiFetch, toQueryString } from '../services/api/client'

// ── Types ────────────────────────────────────────────────────────

interface AuditEntry {
  id: number
  agent_id: string
  user_id: string | null
  endpoint: string
  method: string
  decision: 'allowed' | 'denied' | 'error'
  cost_estimate_usd: number | null
  latency_ms: number | null
  request_metadata: Record<string, unknown>
  entry_hash: string
  prev_hash: string
  created_at: string
}

interface AuditListResponse {
  items: AuditEntry[]
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

function decisionBadge(d: string) {
  switch (d) {
    case 'allowed':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
    case 'denied':
      return 'bg-red-500/10 text-red-400 border-red-500/20'
    default:
      return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
  }
}

// ── Component ────────────────────────────────────────────────────

export function CompliancePage() {
  // Audit log state
  const [entries, setEntries] = useState<AuditEntry[]>([])
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

  useEffect(() => {
    async function loadStats() {
      try {
        const [all, allows, denies, errors] = await Promise.all([
          apiFetch<AuditListResponse>('/api/v1/audit?limit=1'),
          apiFetch<AuditListResponse>('/api/v1/audit?limit=1&decision=allowed'),
          apiFetch<AuditListResponse>('/api/v1/audit?limit=1&decision=denied'),
          apiFetch<AuditListResponse>('/api/v1/audit?limit=1&decision=error'),
        ])
        setStats({
          totalEntries: all.total,
          allowCount: allows.total,
          denyCount: denies.total,
          errorCount: errors.total,
        })
      } catch {
        // Stats failed — non-critical
      }
    }
    loadStats()
  }, [])

  // ── Verify chain ─────────────────────────────────────────────

  const runVerify = async () => {
    setVerifying(true)
    try {
      const data = await apiFetch<VerifyResponse>('/api/v1/audit/verify')
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Compliance & Audit</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-[#71717a]">
            SOC 2-ready audit trail with HMAC-SHA256 integrity verification
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportCSV}
            className="rounded-lg border border-[#1a1a1d] bg-[#111113] px-3 py-2 text-sm text-gray-300 hover:border-[#F59E0B]/30 hover:text-white transition-colors"
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
            className="rounded-lg border border-[#1a1a1d] bg-[#111113] px-3 py-2 text-sm text-gray-300 hover:border-[#F59E0B]/30 hover:text-white transition-colors"
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
        <div className="rounded-xl border border-[#1a1a1d] bg-[#111113]/80 backdrop-blur-xl p-5">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Chain Integrity
            </p>
            <div
              className={`h-3 w-3 rounded-full ${
                verifyResult === null
                  ? 'bg-gray-600'
                  : verifyResult.valid
                    ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]'
                    : 'bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.5)]'
              }`}
            />
          </div>
          <p className="mt-2 text-2xl font-bold text-white">
            {verifyResult === null ? '—' : verifyResult.valid ? 'VALID' : 'BROKEN'}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {lastVerified ? `Last checked ${lastVerified}` : 'Not yet verified'}
          </p>
          <button
            onClick={runVerify}
            disabled={verifying}
            className="mt-3 w-full rounded-lg bg-[#F59E0B]/10 px-3 py-1.5 text-xs font-medium text-[#F59E0B] hover:bg-[#F59E0B]/20 transition-colors disabled:opacity-50"
          >
            {verifying ? 'Verifying...' : 'Verify Now'}
          </button>
        </div>

        {/* Total Entries */}
        <div className="rounded-xl border border-[#1a1a1d] bg-[#111113]/80 backdrop-blur-xl p-5">
          <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
            Total Entries
          </p>
          <p className="mt-2 text-2xl font-bold text-white">
            {stats.totalEntries.toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-gray-500">Append-only audit records</p>
        </div>

        {/* Allow / Deny */}
        <div className="rounded-xl border border-[#1a1a1d] bg-[#111113]/80 backdrop-blur-xl p-5">
          <p className="text-xs font-medium uppercase tracking-wider text-gray-400">Decisions</p>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="text-2xl font-bold text-emerald-400">{stats.allowCount}</span>
            <span className="text-sm text-gray-500">allowed</span>
          </div>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="text-lg font-bold text-red-400">{stats.denyCount}</span>
            <span className="text-sm text-gray-500">denied</span>
            {stats.errorCount > 0 && (
              <>
                <span className="text-lg font-bold text-yellow-400">{stats.errorCount}</span>
                <span className="text-sm text-gray-500">errors</span>
              </>
            )}
          </div>
        </div>

        {/* Compliance Score */}
        <div className="rounded-xl border border-[#1a1a1d] bg-[#111113]/80 backdrop-blur-xl p-5">
          <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
            Compliance Readiness
          </p>
          <p className="mt-2 text-2xl font-bold text-[#F59E0B]">SOC 2</p>
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
              <span className="text-gray-400">HMAC integrity chain</span>
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
              <span className="text-gray-400">Append-only enforcement</span>
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
              <span className="text-gray-400">PII sanitization</span>
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
              <span className="text-gray-400">Tenant isolation (RLS)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Verification detail banner */}
      {verifyResult && (
        <div
          className={`rounded-xl border p-4 ${
            verifyResult.valid
              ? 'border-emerald-500/30 bg-emerald-500/5'
              : 'border-red-500/30 bg-red-500/5'
          }`}
        >
          <div className="flex items-start gap-3">
            <div
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                verifyResult.valid ? 'bg-emerald-500/20' : 'bg-red-500/20'
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
                className={`text-sm font-medium ${verifyResult.valid ? 'text-emerald-400' : 'text-red-400'}`}
              >
                {verifyResult.message}
              </p>
              <p className="mt-0.5 text-xs text-gray-500">
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
          className="rounded-lg border border-[#1a1a1d] bg-[#111113] px-3 py-2 text-sm text-gray-300 focus:border-[#F59E0B]/50 focus:outline-none"
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
          className="rounded-lg border border-[#1a1a1d] bg-[#111113] px-3 py-2 text-sm text-gray-300 placeholder:text-gray-600 focus:border-[#F59E0B]/50 focus:outline-none"
        />

        <span className="text-xs text-gray-500">
          {total} {total === 1 ? 'entry' : 'entries'}
        </span>
      </div>

      {/* Audit log table */}
      <div className="overflow-hidden rounded-xl border border-[#1a1a1d]">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1a1a1d] bg-[#111113]">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                  #
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                  Timestamp
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                  Agent
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                  Endpoint
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                  Method
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                  Decision
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                  Details
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                  Hash
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1a1a1d]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-2 w-2 animate-bounce rounded-full bg-[#F59E0B]" />
                      <div
                        className="h-2 w-2 animate-bounce rounded-full bg-[#F59E0B]"
                        style={{ animationDelay: '0.15s' }}
                      />
                      <div
                        className="h-2 w-2 animate-bounce rounded-full bg-[#F59E0B]"
                        style={{ animationDelay: '0.3s' }}
                      />
                    </div>
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
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
                    className="bg-[#0A0A0B] hover:bg-[#111113]/50 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{entry.id}</td>
                    <td className="px-4 py-3 text-xs text-gray-300 whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">
                      {entry.agent_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-white">{entry.endpoint}</td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-[#1a1a1d] px-1.5 py-0.5 font-mono text-xs text-gray-300">
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
                    <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px] truncate">
                      {entry.request_metadata?.deny_reason
                        ? String(entry.request_metadata.deny_reason)
                        : entry.latency_ms
                          ? `${entry.latency_ms}ms`
                          : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="font-mono text-xs text-gray-600 cursor-help"
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
          <div className="flex items-center justify-between border-t border-[#1a1a1d] bg-[#111113] px-4 py-3">
            <p className="text-xs text-gray-500">
              Page {currentPage} of {totalPages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="rounded-lg border border-[#1a1a1d] px-3 py-1.5 text-xs text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="rounded-lg border border-[#1a1a1d] px-3 py-1.5 text-xs text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Hash chain visualization */}
      {entries.length > 0 && (
        <div className="rounded-xl border border-[#1a1a1d] bg-[#111113]/80 p-5">
          <h3 className="text-sm font-medium text-white">HMAC Chain Visualization</h3>
          <p className="mt-1 text-xs text-gray-500">
            Each entry's hash includes the previous entry's hash, creating a tamper-evident chain
          </p>
          <div className="mt-4 flex items-center gap-2 overflow-x-auto pb-2">
            {entries.slice(0, 8).map((entry, i) => (
              <div key={entry.id} className="flex items-center gap-2 shrink-0">
                <div
                  className={`rounded-lg border px-3 py-2 text-center ${
                    entry.decision === 'allowed'
                      ? 'border-emerald-500/20 bg-emerald-500/5'
                      : entry.decision === 'denied'
                        ? 'border-red-500/20 bg-red-500/5'
                        : 'border-yellow-500/20 bg-yellow-500/5'
                  }`}
                >
                  <p className="font-mono text-[10px] text-gray-500">#{entry.id}</p>
                  <p
                    className={`text-xs font-medium ${
                      entry.decision === 'allowed'
                        ? 'text-emerald-400'
                        : entry.decision === 'denied'
                          ? 'text-red-400'
                          : 'text-yellow-400'
                    }`}
                  >
                    {entry.decision}
                  </p>
                  <p className="mt-0.5 font-mono text-[9px] text-gray-600">
                    {entry.entry_hash.slice(0, 8)}
                  </p>
                </div>
                {i < Math.min(entries.length, 8) - 1 && (
                  <svg
                    width="20"
                    height="12"
                    viewBox="0 0 20 12"
                    className="text-[#F59E0B]/40 shrink-0"
                  >
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
              <span className="text-xs text-gray-500 shrink-0">+{entries.length - 8} more</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
