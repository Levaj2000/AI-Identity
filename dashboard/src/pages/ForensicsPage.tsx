/**
 * ForensicsPage — AI Forensics dashboard for incident investigation.
 *
 * Timeline view, stats, filtering, incident reconstruction,
 * and exportable forensics reports with chain-of-custody verification.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router'
import type {
  Agent,
  AuditLogEntry,
  AuditStatsResponse,
  AuditReconstructResponse,
  ForensicsFilterParams,
} from '../types/api'
import { apiFetch } from '../services/api/client'
import {
  fetchAuditLogs,
  fetchAuditStats,
  fetchAuditReconstruct,
  verifyAuditChain,
} from '../services/api/forensics'
import { ForensicsTimeline } from '../components/forensics/ForensicsTimeline'
import { IncidentReconstructModal } from '../components/forensics/IncidentReconstructModal'
import { EventDetailDrawer } from '../components/forensics/EventDetailDrawer'
import { detectAnomalies } from '../components/forensics/anomalyDetection'
import { HashChainView } from '../components/forensics/HashChainView'

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
  if (d === 'allow' || d === 'allowed')
    return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (d === 'deny' || d === 'denied') return 'bg-red-500/10 text-red-400 border-red-500/20'
  return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
}

/** Default to last 7 days. */
function defaultStartDate(): string {
  const d = new Date()
  d.setDate(d.getDate() - 7)
  return d.toISOString().slice(0, 16)
}

function defaultEndDate(): string {
  return new Date().toISOString().slice(0, 16)
}

// ── Component ────────────────────────────────────────────────────

export function ForensicsPage() {
  // Agents list
  const [agents, setAgents] = useState<Agent[]>([])

  // Filters
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [startDate, setStartDate] = useState(defaultStartDate())
  const [endDate, setEndDate] = useState(defaultEndDate())
  const [filterDecision, setFilterDecision] = useState<string>('')
  const [filterEndpoint, setFilterEndpoint] = useState<string>('')
  const [filterActionType, setFilterActionType] = useState<string>('')
  const [filterModel, setFilterModel] = useState<string>('')
  const [filterCostMin, setFilterCostMin] = useState<string>('')
  const [filterCostMax, setFilterCostMax] = useState<string>('')

  // Data
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<AuditStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const limit = 50

  // View mode
  const [viewMode, setViewMode] = useState<'timeline' | 'table'>('timeline')

  // Chain verification
  const [chainValid, setChainValid] = useState<boolean | null>(null)
  const [chainMessage, setChainMessage] = useState<string>('')

  // Incident reconstruction
  const [reconstructData, setReconstructData] = useState<AuditReconstructResponse | null>(null)
  const [reconstructing, setReconstructing] = useState(false)

  // Hydrate from URL search params (e.g. linked from Shadow Agents page)
  const [searchParams] = useSearchParams()
  const hydrated = useRef(false)
  useEffect(() => {
    if (hydrated.current) return
    hydrated.current = true
    const qAgent = searchParams.get('agent_id')
    const qStart = searchParams.get('start')
    const qEnd = searchParams.get('end')
    if (qAgent) setSelectedAgent(qAgent)
    if (qStart) setStartDate(qStart)
    if (qEnd) setEndDate(qEnd)
  }, [searchParams])

  // Event detail drawer
  const [selectedEvent, setSelectedEvent] = useState<AuditLogEntry | null>(null)

  // ── Fetch agents ──────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false
    apiFetch<{ items: Agent[] }>('/api/v1/agents?limit=100')
      .then((data) => {
        if (!cancelled) setAgents(data.items)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  // ── Fetch audit entries ───────────────────────────────────────

  const loadEntries = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number | undefined> = {
        limit,
        offset,
      }
      if (selectedAgent) params.agent_id = selectedAgent
      if (filterDecision) params.decision = filterDecision
      if (startDate) params.start_date = new Date(startDate).toISOString()
      if (endDate) params.end_date = new Date(endDate).toISOString()
      if (filterEndpoint) params.endpoint = filterEndpoint
      if (filterActionType) params.action_type = filterActionType
      if (filterModel) params.model = filterModel
      if (filterCostMin) params.cost_min = parseFloat(filterCostMin)
      if (filterCostMax) params.cost_max = parseFloat(filterCostMax)

      const data = await fetchAuditLogs(params as ForensicsFilterParams)
      setEntries(data.items)
      setTotal(data.total)
    } catch {
      setEntries([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [
    selectedAgent,
    filterDecision,
    startDate,
    endDate,
    filterEndpoint,
    filterActionType,
    filterModel,
    filterCostMin,
    filterCostMax,
    offset,
  ])

  useEffect(() => {
    loadEntries()
  }, [loadEntries])

  // ── Fetch stats ───────────────────────────────────────────────

  useEffect(() => {
    const params: Record<string, string | undefined> = {}
    if (selectedAgent) params.agent_id = selectedAgent
    if (startDate) params.start_date = new Date(startDate).toISOString()
    if (endDate) params.end_date = new Date(endDate).toISOString()

    fetchAuditStats(params)
      .then(setStats)
      .catch(() => setStats(null))
  }, [selectedAgent, startDate, endDate])

  // ── Verify chain (on-demand only — expensive call) ────────────

  const [chainVerifying, setChainVerifying] = useState(false)

  const handleVerifyChain = useCallback(async () => {
    setChainVerifying(true)
    try {
      const r = await verifyAuditChain(selectedAgent || undefined)
      setChainValid(r.valid)
      setChainMessage(r.message)
    } catch {
      setChainValid(null)
      setChainMessage('')
    } finally {
      setChainVerifying(false)
    }
  }, [selectedAgent])

  // Reset chain status when agent changes
  useEffect(() => {
    setChainValid(null)
    setChainMessage('')
  }, [selectedAgent])

  // ── Incident reconstruction ───────────────────────────────────

  const handleReconstruct = async () => {
    if (!selectedAgent) return
    setReconstructing(true)
    try {
      const data = await fetchAuditReconstruct({
        agent_id: selectedAgent,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      })
      setReconstructData(data)
    } catch {
      alert('Failed to reconstruct incident')
    } finally {
      setReconstructing(false)
    }
  }

  // ── Export ────────────────────────────────────────────────────

  const exportJSON = () => {
    const report = reconstructData || { events: entries, stats }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `forensics-report-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportCSV = () => {
    const rows = [
      [
        'id',
        'agent_id',
        'endpoint',
        'method',
        'decision',
        'cost_usd',
        'latency_ms',
        'created_at',
        'entry_hash',
      ].join(','),
      ...entries.map((e) =>
        [
          e.id,
          e.agent_id,
          e.endpoint,
          e.method,
          e.decision,
          e.cost_estimate_usd ?? '',
          e.latency_ms ?? '',
          e.created_at,
          e.entry_hash,
        ].join(','),
      ),
    ].join('\n')
    const blob = new Blob([rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `forensics-export-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  // ── Pagination ────────────────────────────────────────────────

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  // Anomaly detection for table view highlighting
  const anomalyMap = useMemo(() => detectAnomalies(entries), [entries])

  // ── Render ────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">AI Forensics</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Reconstruct agent decisions with tamper-evident audit chains
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Chain verification — on-demand */}
          {chainValid !== null ? (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                chainValid
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-red-500/10 text-red-400 border border-red-500/20'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${chainValid ? 'bg-emerald-400' : 'bg-red-400'}`}
              />
              Chain {chainValid ? 'Intact' : 'Broken'}
              {chainMessage && <span className="sr-only">{chainMessage}</span>}
            </span>
          ) : (
            <button
              onClick={handleVerifyChain}
              disabled={chainVerifying}
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border border-zinc-600 text-zinc-400 hover:text-zinc-200 hover:border-zinc-500 transition-colors disabled:opacity-50"
            >
              {chainVerifying ? (
                <>
                  <svg
                    className="h-3 w-3 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Verifying...
                </>
              ) : (
                <>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-3.5 w-3.5"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.403 12.652a3 3 0 000-5.304 3 3 0 00-3.75-3.751 3 3 0 00-5.305 0 3 3 0 00-3.751 3.75 3 3 0 000 5.305 3 3 0 003.75 3.751 3 3 0 005.305 0 3 3 0 003.751-3.75zm-2.546-4.46a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Verify Chain
                </>
              )}
            </button>
          )}

          <button
            onClick={exportCSV}
            className="px-3 py-2 text-sm font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors border border-zinc-600"
          >
            CSV
          </button>
          <button
            onClick={exportJSON}
            className="px-3 py-2 text-sm font-medium text-zinc-100 bg-sky-400/90 hover:bg-sky-300/90 rounded-lg transition-colors"
          >
            Export JSON
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Agent selector */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Agent</label>
            <select
              value={selectedAgent}
              onChange={(e) => {
                setSelectedAgent(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-zinc-800 border border-zinc-600 text-zinc-200 text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-sky-400"
            >
              <option value="">All Agents</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.id.slice(0, 8)})
                </option>
              ))}
            </select>
          </div>

          {/* Start date */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">From</label>
            <input
              type="datetime-local"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-zinc-800 border border-zinc-600 text-zinc-200 text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-sky-400"
            />
          </div>

          {/* End date */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">To</label>
            <input
              type="datetime-local"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-zinc-800 border border-zinc-600 text-zinc-200 text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-sky-400"
            />
          </div>

          {/* Decision filter */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Decision</label>
            <select
              value={filterDecision}
              onChange={(e) => {
                setFilterDecision(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-zinc-800 border border-zinc-600 text-zinc-200 text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-sky-400"
            >
              <option value="">All</option>
              <option value="allowed">Allowed</option>
              <option value="denied">Denied</option>
              <option value="error">Error</option>
            </select>
          </div>

          {/* Endpoint search */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Endpoint</label>
            <input
              type="text"
              value={filterEndpoint}
              onChange={(e) => {
                setFilterEndpoint(e.target.value)
                setOffset(0)
              }}
              placeholder="/v1/chat"
              className="w-full rounded-lg bg-zinc-800 border border-zinc-600 text-zinc-200 text-sm px-3 py-2 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-sky-400"
            />
          </div>
        </div>

        {/* Metadata filters row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-3">
          {/* Action type */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Action Type</label>
            <select
              value={filterActionType}
              onChange={(e) => {
                setFilterActionType(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-zinc-800 border border-zinc-600 text-zinc-200 text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-sky-400"
            >
              <option value="">All</option>
              <option value="agent_created">agent_created</option>
              <option value="key_rotated">key_rotated</option>
              <option value="policy_updated">policy_updated</option>
              <option value="credential_stored">credential_stored</option>
              <option value="agent_suspended">agent_suspended</option>
              <option value="agent_deleted">agent_deleted</option>
            </select>
          </div>

          {/* Model */}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Model</label>
            <select
              value={filterModel}
              onChange={(e) => {
                setFilterModel(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-zinc-800 border border-zinc-600 text-zinc-200 text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-sky-400"
            >
              <option value="">All</option>
              <option value="gpt-4">gpt-4</option>
              <option value="gpt-4o">gpt-4o</option>
              <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
              <option value="claude-3-opus">claude-3-opus</option>
              <option value="claude-3-sonnet">claude-3-sonnet</option>
              <option value="claude-3-haiku">claude-3-haiku</option>
            </select>
          </div>

          {/* Cost range */}
          <div className="sm:col-span-2">
            <label className="block text-xs text-zinc-500 mb-1">Cost Range (USD)</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={filterCostMin}
                onChange={(e) => {
                  setFilterCostMin(e.target.value)
                  setOffset(0)
                }}
                placeholder="Min"
                step="0.001"
                min="0"
                className="w-full rounded-lg bg-zinc-800 border border-zinc-600 text-zinc-200 text-sm px-3 py-2 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-sky-400"
              />
              <span className="text-zinc-500 text-sm">–</span>
              <input
                type="number"
                value={filterCostMax}
                onChange={(e) => {
                  setFilterCostMax(e.target.value)
                  setOffset(0)
                }}
                placeholder="Max"
                step="0.001"
                min="0"
                className="w-full rounded-lg bg-zinc-800 border border-zinc-600 text-zinc-200 text-sm px-3 py-2 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-sky-400"
              />
            </div>
          </div>
        </div>

        {/* Investigate button */}
        {selectedAgent && (
          <div className="mt-3 pt-3 border-t border-zinc-700">
            <button
              onClick={handleReconstruct}
              disabled={reconstructing}
              className="px-4 py-2 text-sm font-medium text-zinc-100 bg-sky-400/90 hover:bg-sky-300/90 disabled:opacity-50 rounded-lg transition-colors inline-flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" />
              </svg>
              {reconstructing ? 'Reconstructing...' : 'Investigate Incident'}
            </button>
          </div>
        )}
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wider">Total Events</div>
            <div className="text-2xl font-bold text-[#A6DAFF] mt-1">
              {stats.total_events.toLocaleString()}
            </div>
          </div>
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4">
            <div className="text-xs text-emerald-400 uppercase tracking-wider">Allowed</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              {stats.allowed_count.toLocaleString()}
            </div>
          </div>
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4">
            <div className="text-xs text-red-400 uppercase tracking-wider">Denied</div>
            <div className="text-2xl font-bold text-red-400 mt-1">
              {stats.denied_count.toLocaleString()}
            </div>
          </div>
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4">
            <div className="text-xs text-yellow-400 uppercase tracking-wider">Errors</div>
            <div className="text-2xl font-bold text-yellow-400 mt-1">
              {stats.error_count.toLocaleString()}
            </div>
          </div>
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wider">Total Cost</div>
            <div className="text-2xl font-bold text-zinc-100 mt-1">
              ${stats.total_cost_usd.toFixed(2)}
            </div>
          </div>
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wider">Avg Latency</div>
            <div className="text-2xl font-bold text-zinc-100 mt-1">
              {stats.avg_latency_ms != null ? `${stats.avg_latency_ms}ms` : '--'}
            </div>
          </div>
        </div>
      )}

      {/* View Toggle + Results Count */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-zinc-500">
          {total.toLocaleString()} event{total !== 1 ? 's' : ''} found
        </div>
        <div className="flex items-center gap-1 bg-zinc-800 rounded-lg p-0.5 border border-zinc-700">
          <button
            onClick={() => setViewMode('timeline')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'timeline'
                ? 'bg-[#A6DAFF] text-[#04070D]'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Timeline
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'table'
                ? 'bg-[#A6DAFF] text-[#04070D]'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Table
          </button>
        </div>
      </div>

      {/* Hash Chain Visualization */}
      {entries.length > 1 && <HashChainView events={entries} />}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-500">
          Loading audit events...
        </div>
      ) : viewMode === 'timeline' ? (
        <div className="bg-zinc-800/30 border border-zinc-700 rounded-xl p-6">
          <ForensicsTimeline events={entries} onEventClick={setSelectedEvent} />
        </div>
      ) : (
        /* Table View */
        <div className="bg-zinc-800/30 border border-zinc-700 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-700 text-left text-xs text-zinc-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Decision</th>
                  <th className="px-4 py-3">Method</th>
                  <th className="px-4 py-3">Endpoint</th>
                  <th className="px-4 py-3">Cost</th>
                  <th className="px-4 py-3">Latency</th>
                  <th className="px-4 py-3">Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {entries.map((e) => {
                  const rowAnomalies = anomalyMap.get(e.id)
                  const hasDenyCluster = rowAnomalies?.some((a) => a.type === 'deny_cluster')
                  const hasLatencyOrCost = rowAnomalies?.some(
                    (a) => a.type === 'latency_spike' || a.type === 'cost_outlier',
                  )
                  const rowBg = hasDenyCluster
                    ? 'bg-red-500/5'
                    : hasLatencyOrCost
                      ? 'bg-orange-500/5'
                      : ''
                  return (
                    <tr
                      key={e.id}
                      className={`hover:bg-zinc-800/50 transition-colors cursor-pointer ${rowBg}`}
                      onClick={() => setSelectedEvent(e)}
                    >
                      <td className="px-4 py-3 text-zinc-300 whitespace-nowrap">
                        {formatDate(e.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${decisionBadge(e.decision)}`}
                        >
                          {e.decision}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-400 font-mono text-xs">{e.method}</td>
                      <td className="px-4 py-3 text-zinc-300 font-mono text-xs max-w-xs truncate">
                        {e.endpoint}
                      </td>
                      <td className="px-4 py-3 text-zinc-400">
                        {e.cost_estimate_usd != null ? `$${e.cost_estimate_usd.toFixed(4)}` : '--'}
                      </td>
                      <td className="px-4 py-3 text-zinc-400">
                        {e.latency_ms != null ? `${e.latency_ms}ms` : '--'}
                      </td>
                      <td className="px-4 py-3 text-zinc-600 font-mono text-xs">
                        {e.entry_hash.slice(0, 12)}...
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-sm text-zinc-500">
            Page {currentPage} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              className="px-3 py-1.5 text-sm font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 rounded-lg transition-colors border border-zinc-600"
            >
              Previous
            </button>
            <button
              onClick={() => setOffset(offset + limit)}
              disabled={offset + limit >= total}
              className="px-3 py-1.5 text-sm font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 rounded-lg transition-colors border border-zinc-600"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Top Endpoints */}
      {stats && stats.top_endpoints.length > 0 && (
        <div className="bg-zinc-800/30 border border-zinc-700 rounded-xl p-6">
          <h3 className="text-sm font-medium text-zinc-300 mb-3">Top Endpoints</h3>
          <div className="space-y-2">
            {stats.top_endpoints.map((ep) => {
              const pct = stats.total_events > 0 ? (ep.count / stats.total_events) * 100 : 0
              return (
                <div key={ep.endpoint} className="flex items-center gap-3">
                  <span className="text-xs font-mono text-zinc-400 w-48 truncate">
                    {ep.endpoint}
                  </span>
                  <div className="flex-1 bg-zinc-700/50 rounded-full h-2">
                    <div
                      className="bg-[#A6DAFF] h-2 rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-zinc-500 w-16 text-right">
                    {ep.count} ({pct.toFixed(0)}%)
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Incident Reconstruction Modal */}
      {reconstructData && (
        <IncidentReconstructModal
          data={reconstructData}
          onClose={() => setReconstructData(null)}
          onExportJSON={exportJSON}
          onExportCSV={exportCSV}
        />
      )}

      {/* Event Detail Drawer */}
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
