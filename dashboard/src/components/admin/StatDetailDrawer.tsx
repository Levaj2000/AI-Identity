/**
 * StatDetailDrawer -- slide-out panel for admin stat card details.
 *
 * Modes: users | agents | requests | health
 * Reuses the right-side drawer pattern from EventDetailDrawer.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getAdminUsers,
  getAdminAgents,
  getAdminHealth,
  type AdminUserList,
  type AdminAgentList,
  type AdminHealth,
} from '../../services/api/admin'

export type StatDrawerMode = 'users' | 'agents' | 'requests' | 'health'

interface Props {
  mode: StatDrawerMode
  onClose: () => void
}

export function StatDetailDrawer({ mode, onClose }: Props) {
  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-[#10131C] border-l border-[#1a1a1d] z-50 overflow-y-auto shadow-2xl animate-slide-in flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-[#10131C]/95 backdrop-blur border-b border-[#1a1a1d] px-6 py-4 flex items-center justify-between z-10 shrink-0">
          <h2 className="text-lg font-semibold text-white">{drawerTitle(mode)}</h2>
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
        <div className="flex-1 overflow-y-auto">
          {mode === 'users' && <UsersPanel />}
          {mode === 'agents' && <AgentsPanel />}
          {mode === 'requests' && <RequestsPanel />}
          {mode === 'health' && <HealthPanel />}
        </div>
      </div>
    </>
  )
}

function drawerTitle(mode: StatDrawerMode): string {
  switch (mode) {
    case 'users':
      return 'All Users'
    case 'agents':
      return 'All Agents'
    case 'requests':
      return 'Top Requesters'
    case 'health':
      return 'System Health'
  }
}

// ── Users Panel ──────────────────────────────────────────────────

function UsersPanel() {
  const [data, setData] = useState<AdminUserList | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 20

  const load = async (s?: string, p?: number) => {
    setLoading(true)
    try {
      const params: { limit: number; offset: number; search?: string } = {
        limit: pageSize,
        offset: (p ?? page) * pageSize,
      }
      if (s ?? search) params.search = s ?? search
      const res = await getAdminUsers(params)
      setData(res)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => {
    setPage(0)
    load(search, 0)
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0

  return (
    <div className="px-6 py-5 space-y-4">
      {/* Search */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Search by email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="flex-1 px-3 py-1.5 bg-[#04070D] border border-[#1a1a1d] rounded-lg text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-[#A6DAFF]/50"
        />
        <button
          onClick={handleSearch}
          className="px-3 py-1.5 bg-[#A6DAFF]/10 text-[#A6DAFF] rounded-lg text-sm hover:bg-[#A6DAFF]/20 transition-colors"
        >
          Search
        </button>
      </div>

      {loading && !data ? (
        <div className="text-gray-500 text-sm py-8 text-center">Loading...</div>
      ) : (
        <>
          <div className="text-xs text-gray-500">{data?.total ?? 0} total users</div>
          <div className="space-y-2">
            {data?.items.map((u) => (
              <div
                key={u.id}
                className="bg-[#04070D] border border-[#1a1a1d] rounded-lg px-4 py-3 flex items-center justify-between"
              >
                <div className="min-w-0">
                  <Link
                    to={`/dashboard/admin/users/${u.id}`}
                    className="text-sm text-[#A6DAFF] hover:underline truncate block"
                  >
                    {u.email || '--'}
                  </Link>
                  <div className="text-xs text-gray-500 mt-0.5 flex gap-3">
                    <span>{u.agent_count} agents</span>
                    <span>{u.requests_this_month.toLocaleString()} reqs</span>
                    {u.created_at && <span>{new Date(u.created_at).toLocaleDateString()}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  <TierBadge tier={u.tier} />
                  {u.has_subscription ? (
                    <span
                      className="w-2 h-2 bg-green-400 rounded-full"
                      title="Active subscription"
                    />
                  ) : (
                    <span className="w-2 h-2 bg-gray-600 rounded-full" title="No subscription" />
                  )}
                </div>
              </div>
            ))}
            {data?.items.length === 0 && (
              <div className="text-gray-500 text-sm py-8 text-center">No users found</div>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <PaginationControls
              page={page}
              totalPages={totalPages}
              total={data?.total ?? 0}
              pageSize={pageSize}
              onPageChange={(p) => {
                setPage(p)
                load(search, p)
              }}
            />
          )}
        </>
      )}
    </div>
  )
}

// ── Agents Panel ─────────────────────────────────────────────────

function AgentsPanel() {
  const [data, setData] = useState<AdminAgentList | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 20

  const load = async (s?: string, st?: string, p?: number) => {
    setLoading(true)
    try {
      const params: { limit: number; offset: number; search?: string; status?: string } = {
        limit: pageSize,
        offset: (p ?? page) * pageSize,
      }
      if (s ?? search) params.search = s ?? search
      if (st ?? statusFilter) params.status = st ?? statusFilter
      const res = await getAdminAgents(params)
      setData(res)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => {
    setPage(0)
    load(search, statusFilter, 0)
  }

  const handleStatusChange = (st: string) => {
    setStatusFilter(st)
    setPage(0)
    load(search, st, 0)
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0

  return (
    <div className="px-6 py-5 space-y-4">
      {/* Search + filter */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Search by name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="flex-1 px-3 py-1.5 bg-[#04070D] border border-[#1a1a1d] rounded-lg text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-[#A6DAFF]/50"
        />
        <select
          value={statusFilter}
          onChange={(e) => handleStatusChange(e.target.value)}
          className="px-3 py-1.5 bg-[#04070D] border border-[#1a1a1d] rounded-lg text-sm text-white focus:outline-none focus:border-[#A6DAFF]/50"
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="revoked">Revoked</option>
        </select>
        <button
          onClick={handleSearch}
          className="px-3 py-1.5 bg-[#A6DAFF]/10 text-[#A6DAFF] rounded-lg text-sm hover:bg-[#A6DAFF]/20 transition-colors"
        >
          Search
        </button>
      </div>

      {loading && !data ? (
        <div className="text-gray-500 text-sm py-8 text-center">Loading...</div>
      ) : (
        <>
          <div className="text-xs text-gray-500">{data?.total ?? 0} total agents</div>
          <div className="space-y-2">
            {data?.items.map((a) => (
              <div
                key={a.id}
                className="bg-[#04070D] border border-[#1a1a1d] rounded-lg px-4 py-3 flex items-center justify-between"
              >
                <div className="min-w-0">
                  <div className="text-sm text-white truncate">{a.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5 flex gap-3">
                    <span>{a.owner_email || '--'}</span>
                    <span>{a.key_count} keys</span>
                    {a.created_at && <span>{new Date(a.created_at).toLocaleDateString()}</span>}
                  </div>
                </div>
                <StatusBadge status={a.status} />
              </div>
            ))}
            {data?.items.length === 0 && (
              <div className="text-gray-500 text-sm py-8 text-center">No agents found</div>
            )}
          </div>

          {totalPages > 1 && (
            <PaginationControls
              page={page}
              totalPages={totalPages}
              total={data?.total ?? 0}
              pageSize={pageSize}
              onPageChange={(p) => {
                setPage(p)
                load(search, statusFilter, p)
              }}
            />
          )}
        </>
      )}
    </div>
  )
}

// ── Requests Panel ───────────────────────────────────────────────

function RequestsPanel() {
  const [data, setData] = useState<AdminUserList | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        // Fetch users sorted by requests (we get a big page and sort client-side
        // since the existing endpoint doesn't support sort param)
        const res = await getAdminUsers({ limit: 100, offset: 0 })
        res.items.sort((a, b) => b.requests_this_month - a.requests_this_month)
        setData(res)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) {
    return <div className="text-gray-500 text-sm py-8 text-center px-6">Loading...</div>
  }

  return (
    <div className="px-6 py-5 space-y-4">
      <div className="text-xs text-gray-500">Users ranked by requests this month</div>
      <div className="space-y-2">
        {data?.items.map((u, idx) => (
          <div
            key={u.id}
            className="bg-[#04070D] border border-[#1a1a1d] rounded-lg px-4 py-3 flex items-center justify-between"
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-xs text-gray-600 font-mono w-6 text-right shrink-0">
                #{idx + 1}
              </span>
              <div className="min-w-0">
                <div className="text-sm text-white truncate">{u.email || '--'}</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  <TierBadge tier={u.tier} /> &middot; {u.agent_count} agents
                </div>
              </div>
            </div>
            <div className="text-right shrink-0 ml-3">
              <div className="text-sm font-semibold text-[#A6DAFF]">
                {u.requests_this_month.toLocaleString()}
              </div>
              <div className="text-xs text-gray-500">requests</div>
            </div>
          </div>
        ))}
        {data?.items.length === 0 && (
          <div className="text-gray-500 text-sm py-8 text-center">No data</div>
        )}
      </div>
    </div>
  )
}

// ── Health Panel ─────────────────────────────────────────────────

function HealthPanel() {
  const [data, setData] = useState<AdminHealth | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const res = await getAdminHealth()
        setData(res)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) {
    return <div className="text-gray-500 text-sm py-8 text-center px-6">Loading...</div>
  }

  if (!data) {
    return (
      <div className="text-red-400 text-sm py-8 text-center px-6">Failed to load health data</div>
    )
  }

  const latencyColor =
    data.db_latency_ms < 50
      ? 'text-green-400'
      : data.db_latency_ms < 200
        ? 'text-yellow-400'
        : 'text-red-400'
  const latencyBg =
    data.db_latency_ms < 50
      ? 'bg-green-400'
      : data.db_latency_ms < 200
        ? 'bg-yellow-400'
        : 'bg-red-400'

  return (
    <div className="px-6 py-5 space-y-5">
      {/* Overall status */}
      <div className="bg-[#04070D] border border-[#1a1a1d] rounded-lg px-4 py-4">
        <div className="text-xs text-gray-500 mb-2">Overall Status</div>
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${data.status === 'healthy' ? 'bg-green-400' : 'bg-red-400'}`}
          />
          <span className="text-lg font-semibold text-white capitalize">{data.status}</span>
        </div>
      </div>

      {/* DB Latency */}
      <div className="bg-[#04070D] border border-[#1a1a1d] rounded-lg px-4 py-4">
        <div className="text-xs text-gray-500 mb-2">Database Latency</div>
        <div className="flex items-center gap-3">
          <span className={`text-2xl font-semibold ${latencyColor}`}>{data.db_latency_ms}ms</span>
          <div className="flex-1 h-2 bg-[#1a1a1d] rounded-full overflow-hidden">
            <div
              className={`h-full ${latencyBg} rounded-full transition-all`}
              style={{ width: `${Math.min((data.db_latency_ms / 500) * 100, 100)}%` }}
            />
          </div>
        </div>
        <div className="text-xs text-gray-600 mt-1">
          {data.db_latency_ms < 50 ? 'Excellent' : data.db_latency_ms < 200 ? 'Acceptable' : 'Slow'}
        </div>
      </div>

      {/* Table row counts */}
      <div className="bg-[#04070D] border border-[#1a1a1d] rounded-lg px-4 py-4">
        <div className="text-xs text-gray-500 mb-3">Table Row Counts</div>
        <div className="space-y-2">
          {Object.entries(data.table_counts).map(([table, count]) => (
            <div
              key={table}
              className="flex items-center justify-between py-1.5 border-b border-[#1a1a1d]/50 last:border-b-0"
            >
              <span className="text-sm text-gray-300 font-mono">{table}</span>
              <span className="text-sm font-semibold text-white">{count.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Shared subcomponents ─────────────────────────────────────────

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    free: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
    pro: 'bg-[#A6DAFF]/10 text-[#A6DAFF] border-[#A6DAFF]/20',
    enterprise: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  }
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium border ${colors[tier] || colors.free}`}
    >
      {tier.charAt(0).toUpperCase() + tier.slice(1)}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-green-500/10 text-green-400 border-green-500/20',
    suspended: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    revoked: 'bg-red-500/10 text-red-400 border-red-500/20',
  }
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium border ${colors[status] || 'bg-gray-500/10 text-gray-400 border-gray-500/20'}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

function PaginationControls({
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
}: {
  page: number
  totalPages: number
  total: number
  pageSize: number
  onPageChange: (p: number) => void
}) {
  return (
    <div className="flex items-center justify-between pt-2">
      <span className="text-xs text-gray-500">
        {page * pageSize + 1}--{Math.min((page + 1) * pageSize, total)} of {total}
      </span>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 0}
          className="px-3 py-1 text-xs rounded border border-[#1a1a1d] text-gray-300 hover:bg-[#1a1a1d] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          Prev
        </button>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages - 1}
          className="px-3 py-1 text-xs rounded border border-[#1a1a1d] text-gray-300 hover:bg-[#1a1a1d] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          Next
        </button>
      </div>
    </div>
  )
}
