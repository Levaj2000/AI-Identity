import { useEffect, useState, useCallback } from 'react'
import {
  getShadowAgentStats,
  getShadowAgents,
  getShadowAgentDetail,
  type ShadowAgentStats,
  type ShadowAgentList,
  type ShadowAgentDetail,
  type ShadowAgentSummary,
} from '../services/api/shadow'
import { isApiError } from '../services/api/client'

type DenyReasonFilter = '' | 'agent_not_found' | 'agent_inactive'

export function ShadowAgentsPage() {
  const [stats, setStats] = useState<ShadowAgentStats | null>(null)
  const [data, setData] = useState<ShadowAgentList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [denyReasonFilter, setDenyReasonFilter] = useState<DenyReasonFilter>('')
  const [minHits, setMinHits] = useState(1)
  const [page, setPage] = useState(0)
  const [selectedAgent, setSelectedAgent] = useState<ShadowAgentDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const pageSize = 50

  const loadData = useCallback(
    async (reason?: DenyReasonFilter, currentPage?: number) => {
      try {
        setLoading(true)
        setError(null)
        const params: Record<string, string | number> = {
          limit: pageSize,
          offset: (currentPage ?? page) * pageSize,
          min_hits: minHits,
        }
        const r = reason ?? denyReasonFilter
        if (r) params.deny_reason = r

        const [statsRes, listRes] = await Promise.allSettled([
          getShadowAgentStats(),
          getShadowAgents(params),
        ])

        if (statsRes.status === 'fulfilled') setStats(statsRes.value)
        if (listRes.status === 'fulfilled') setData(listRes.value)

        for (const res of [statsRes, listRes]) {
          if (res.status === 'rejected' && isApiError(res.reason) && res.reason.status === 403) {
            setError('Access denied')
            return
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load shadow agents')
      } finally {
        setLoading(false)
      }
    },
    [page, denyReasonFilter, minHits, pageSize],
  )

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleDenyReasonFilter = (reason: DenyReasonFilter) => {
    setDenyReasonFilter(reason)
    setPage(0)
    loadData(reason, 0)
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    loadData(denyReasonFilter, newPage)
  }

  const handleSelectAgent = async (agent: ShadowAgentSummary) => {
    setLoadingDetail(true)
    try {
      const detail = await getShadowAgentDetail(agent.agent_id)
      setSelectedAgent(detail)
    } catch {
      // Silently fail — drawer just doesn't open
    } finally {
      setLoadingDetail(false)
    }
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-red-400">
          <h3 className="font-semibold mb-1">Error</h3>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Shadow Agents</h1>
        <p className="text-gray-400 mt-1">
          Detect unmanaged or unregistered agents hitting your gateway
        </p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Shadow Agents" value={stats.total_shadow_agents} color="red" />
          <StatCard label="Total Hits" value={stats.total_shadow_hits} color="default" />
          <StatCard
            label="Not Found"
            value={stats.agents_not_found}
            sublabel="Unknown agent IDs"
            color="red"
          />
          <StatCard
            label="Inactive"
            value={stats.agents_inactive}
            sublabel="Revoked / suspended"
            color="yellow"
          />
        </div>
      )}

      {/* Filters */}
      <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Deny Reason</label>
          <select
            value={denyReasonFilter}
            onChange={(e) => handleDenyReasonFilter(e.target.value as DenyReasonFilter)}
            className="px-3 py-1.5 bg-[#04070D] border border-[#1a1a1d] rounded-lg text-sm text-white focus:outline-none focus:border-[#A6DAFF]/50"
          >
            <option value="">All</option>
            <option value="agent_not_found">Not Found</option>
            <option value="agent_inactive">Inactive</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Min Hits</label>
          <input
            type="number"
            min={1}
            value={minHits}
            onChange={(e) => setMinHits(Math.max(1, parseInt(e.target.value) || 1))}
            onBlur={() => loadData()}
            className="px-3 py-1.5 bg-[#04070D] border border-[#1a1a1d] rounded-lg text-sm text-white focus:outline-none focus:border-[#A6DAFF]/50 w-20"
          />
        </div>
        <div className="text-xs text-gray-500">Last 7 days</div>
      </div>

      {/* Table */}
      <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl overflow-hidden">
        {loading && !data ? (
          <div className="px-5 py-12 text-center text-gray-500">Scanning for shadow agents...</div>
        ) : data?.items.length === 0 ? (
          <div className="px-5 py-12 text-center text-gray-500">
            <div className="text-3xl mb-2">🛡️</div>
            <div>No shadow agents detected in the last 7 days</div>
            <div className="text-xs mt-1">All gateway traffic is from registered agents</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-[#1a1a1d]">
                  <th className="px-5 py-3 font-medium">Agent ID</th>
                  <th className="px-5 py-3 font-medium">Reason</th>
                  <th className="px-5 py-3 font-medium">Hits</th>
                  <th className="px-5 py-3 font-medium">First Seen</th>
                  <th className="px-5 py-3 font-medium">Last Seen</th>
                  <th className="px-5 py-3 font-medium">Top Endpoints</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((agent) => (
                  <tr
                    key={`${agent.agent_id}-${agent.deny_reason}`}
                    className="border-b border-[#1a1a1d]/50 hover:bg-[#1a1a1d]/30 transition-colors cursor-pointer"
                    onClick={() => handleSelectAgent(agent)}
                  >
                    <td className="px-5 py-3">
                      <span className="font-mono text-xs text-white">
                        {agent.agent_id.slice(0, 12)}...
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <DenyReasonBadge reason={agent.deny_reason} />
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`font-medium ${agent.hit_count >= 10 ? 'text-red-400' : 'text-white'}`}
                      >
                        {agent.hit_count.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-400 whitespace-nowrap">
                      {formatDateTime(agent.first_seen)}
                    </td>
                    <td className="px-5 py-3 text-gray-400 whitespace-nowrap">
                      {formatDateTime(agent.last_seen)}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex flex-wrap gap-1">
                        {agent.top_endpoints.slice(0, 2).map((ep) => (
                          <span
                            key={ep}
                            className="text-xs font-mono text-gray-400 bg-[#1a1a1d] px-1.5 py-0.5 rounded"
                          >
                            {ep}
                          </span>
                        ))}
                        {agent.top_endpoints.length > 2 && (
                          <span className="text-xs text-gray-500">
                            +{agent.top_endpoints.length - 2}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-[#1a1a1d]">
            <span className="text-sm text-gray-400">
              Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, data?.total || 0)} of{' '}
              {data?.total || 0}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 0}
                className="px-3 py-1 text-sm rounded border border-[#1a1a1d] text-gray-300 hover:bg-[#1a1a1d] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages - 1}
                className="px-3 py-1 text-sm rounded border border-[#1a1a1d] text-gray-300 hover:bg-[#1a1a1d] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedAgent && (
        <ShadowDetailDrawer detail={selectedAgent} onClose={() => setSelectedAgent(null)} />
      )}

      {/* Loading overlay for detail fetch */}
      {loadingDetail && (
        <div className="fixed inset-0 bg-black/30 z-40 flex items-center justify-center">
          <div className="text-gray-400 text-sm">Loading detail...</div>
        </div>
      )}
    </div>
  )
}

// ── Detail Drawer ───────────────────────────────────────────────────

function ShadowDetailDrawer({
  detail,
  onClose,
}: {
  detail: ShadowAgentDetail
  onClose: () => void
}) {
  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      <div className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-[#10131C] border-l border-[#1a1a1d] z-50 overflow-y-auto shadow-2xl flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-[#10131C]/95 backdrop-blur border-b border-[#1a1a1d] px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-lg font-semibold text-white">Shadow Agent</h2>
            <p className="text-xs text-gray-500 font-mono mt-0.5">{detail.agent_id}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-white rounded transition-colors"
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
        <div className="flex-1 p-6 space-y-6">
          {/* Summary */}
          <div className="flex items-center gap-3">
            <DenyReasonBadge reason={detail.deny_reason} large />
            <span className="text-white font-semibold text-lg">
              {detail.hit_count.toLocaleString()} hits
            </span>
          </div>

          {/* Timeline */}
          <div className="bg-[#04070D] border border-[#1a1a1d] rounded-xl p-4 space-y-3 text-sm">
            <h3 className="text-gray-400 font-medium text-xs uppercase tracking-wider">
              Activity Window
            </h3>
            <InfoRow label="First seen" value={formatDateTime(detail.first_seen)} />
            <InfoRow label="Last seen" value={formatDateTime(detail.last_seen)} />
          </div>

          {/* Top Endpoints */}
          <div className="bg-[#04070D] border border-[#1a1a1d] rounded-xl p-4 space-y-3">
            <h3 className="text-gray-400 font-medium text-xs uppercase tracking-wider">
              Endpoints Probed ({detail.top_endpoints.length})
            </h3>
            {detail.top_endpoints.length === 0 ? (
              <p className="text-gray-500 text-sm">No endpoint data</p>
            ) : (
              <div className="space-y-2">
                {detail.top_endpoints.map((ep) => (
                  <div
                    key={`${ep.method}-${ep.endpoint}`}
                    className="flex items-center justify-between text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <MethodBadge method={ep.method} />
                      <span className="font-mono text-xs text-gray-300">{ep.endpoint}</span>
                    </div>
                    <span className="text-gray-400 text-xs">{ep.count}x</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Events */}
          <div className="bg-[#04070D] border border-[#1a1a1d] rounded-xl p-4 space-y-3">
            <h3 className="text-gray-400 font-medium text-xs uppercase tracking-wider">
              Recent Events ({detail.recent_events.length})
            </h3>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {detail.recent_events.map((event) => (
                <div
                  key={event.id}
                  className="flex items-center justify-between text-xs border-b border-[#1a1a1d]/50 pb-2"
                >
                  <div className="flex items-center gap-2">
                    <MethodBadge method={event.method} />
                    <span className="font-mono text-gray-400">{event.endpoint}</span>
                  </div>
                  <span className="text-gray-500 whitespace-nowrap">
                    {formatDateTime(event.created_at)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

// ── Helper Components ───────────────────────────────────────────────

function StatCard({
  label,
  value,
  sublabel,
  color,
}: {
  label: string
  value: number
  sublabel?: string
  color: 'red' | 'yellow' | 'default'
}) {
  const valueColor =
    color === 'red' && value > 0
      ? 'text-red-400'
      : color === 'yellow' && value > 0
        ? 'text-yellow-400'
        : 'text-white'

  return (
    <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl p-5">
      <p className="text-sm text-gray-400">{label}</p>
      <p className={`text-2xl font-semibold mt-1 ${valueColor}`}>{value.toLocaleString()}</p>
      {sublabel && <p className="text-xs text-gray-500 mt-0.5">{sublabel}</p>}
    </div>
  )
}

function DenyReasonBadge({ reason, large }: { reason: string; large?: boolean }) {
  const isNotFound = reason === 'agent_not_found'
  const bg = isNotFound
    ? 'bg-red-500/10 border-red-500/20'
    : 'bg-yellow-500/10 border-yellow-500/20'
  const text = isNotFound ? 'text-red-400' : 'text-yellow-400'
  const dot = isNotFound ? 'bg-red-400' : 'bg-yellow-400'
  const label = isNotFound ? 'Not Found' : 'Inactive'
  const size = large ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-xs'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${bg} ${text} ${size}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  )
}

function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: 'text-green-400',
    POST: 'text-[#A6DAFF]',
    PUT: 'text-yellow-400',
    PATCH: 'text-yellow-400',
    DELETE: 'text-red-400',
  }
  return (
    <span className={`font-mono text-xs font-medium ${colors[method] || 'text-gray-400'}`}>
      {method}
    </span>
  )
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="text-white">{value}</span>
    </div>
  )
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}
