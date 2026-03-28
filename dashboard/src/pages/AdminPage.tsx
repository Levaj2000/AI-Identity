import { useEffect, useState } from 'react'
import {
  getAdminStats,
  getAdminUsers,
  getAdminHealth,
  updateUserTier,
  type AdminStats,
  type AdminUserList,
  type AdminHealth,
} from '../services/api/admin'
import { isApiError } from '../services/api/client'
import { StatDetailDrawer, type StatDrawerMode } from '../components/admin/StatDetailDrawer'

type TierFilter = '' | 'free' | 'pro' | 'enterprise'

export function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<AdminUserList | null>(null)
  const [health, setHealth] = useState<AdminHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [forbidden, setForbidden] = useState(false)

  // Filters
  const [search, setSearch] = useState('')
  const [tierFilter, setTierFilter] = useState<TierFilter>('')
  const [page, setPage] = useState(0)
  const pageSize = 20

  // Tier change state
  const [changingTier, setChangingTier] = useState<string | null>(null)

  // Stat detail drawer
  const [selectedStat, setSelectedStat] = useState<StatDrawerMode | null>(null)

  const loadData = async (currentSearch?: string, currentTier?: string, currentPage?: number) => {
    try {
      setLoading(true)
      setError(null)

      const params: { limit: number; offset: number; search?: string; tier?: string } = {
        limit: pageSize,
        offset: (currentPage ?? page) * pageSize,
      }
      if (currentSearch ?? search) params.search = currentSearch ?? search
      if (currentTier ?? tierFilter) params.tier = currentTier ?? tierFilter

      const [statsRes, usersRes, healthRes] = await Promise.allSettled([
        getAdminStats(),
        getAdminUsers(params),
        getAdminHealth(),
      ])

      if (statsRes.status === 'fulfilled') setStats(statsRes.value)
      if (usersRes.status === 'fulfilled') setUsers(usersRes.value)
      if (healthRes.status === 'fulfilled') setHealth(healthRes.value)

      // Check for 403
      for (const r of [statsRes, usersRes, healthRes]) {
        if (r.status === 'rejected' && isApiError(r.reason) && r.reason.status === 403) {
          setForbidden(true)
          return
        }
      }
    } catch (err) {
      if (isApiError(err) && err.status === 403) {
        setForbidden(true)
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load admin data')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => {
    setPage(0)
    loadData(search, tierFilter, 0)
  }

  const handleTierFilter = (tier: TierFilter) => {
    setTierFilter(tier)
    setPage(0)
    loadData(search, tier, 0)
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    loadData(search, tierFilter, newPage)
  }

  const handleTierChange = async (userId: string, newTier: string) => {
    if (
      !confirm(
        `Change this user's tier to ${newTier.toUpperCase()}? This does NOT sync with Stripe.`,
      )
    )
      return

    setChangingTier(userId)
    try {
      await updateUserTier(userId, newTier)
      await loadData(search, tierFilter, page)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update tier')
    } finally {
      setChangingTier(null)
    }
  }

  if (forbidden) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <div className="text-5xl mb-4">🔒</div>
        <h2 className="text-2xl font-semibold text-white mb-2">Admin Access Required</h2>
        <p className="text-gray-400">
          Your account does not have admin privileges. Contact the platform owner for access.
        </p>
      </div>
    )
  }

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-400">Loading admin dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-red-400">
          <h3 className="font-semibold mb-1">Error loading admin data</h3>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }

  const totalPages = users ? Math.ceil(users.total / pageSize) : 0

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Admin Dashboard</h1>
        <p className="text-gray-400 mt-1">Platform overview and user management</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Total Users"
            value={stats.total_users}
            icon="👥"
            onClick={() => setSelectedStat('users')}
          />
          <StatCard
            label="Total Agents"
            value={stats.total_agents}
            sublabel={`${stats.total_active_agents} active`}
            icon="🤖"
            onClick={() => setSelectedStat('agents')}
          />
          <StatCard
            label="Requests This Month"
            value={stats.total_requests.toLocaleString()}
            icon="📊"
            onClick={() => setSelectedStat('requests')}
          />
          <StatCard
            label="System Health"
            value={health?.status === 'healthy' ? 'Healthy' : 'Unknown'}
            sublabel={health ? `${health.db_latency_ms}ms DB` : undefined}
            icon={health?.status === 'healthy' ? '✅' : '⚠️'}
            onClick={() => setSelectedStat('health')}
          />
        </div>
      )}

      {/* Tier Distribution */}
      {stats && (
        <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Users by Tier</h3>
          <div className="flex gap-4">
            {['free', 'pro', 'enterprise'].map((tier) => (
              <div key={tier} className="flex items-center gap-2">
                <TierBadge tier={tier} />
                <span className="text-white font-medium">{stats.users_by_tier[tier] || 0}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Table Counts */}
      {health && (
        <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Database Tables</h3>
          <div className="flex gap-6">
            {Object.entries(health.table_counts).map(([table, count]) => (
              <div key={table} className="text-sm">
                <span className="text-gray-400">{table}:</span>{' '}
                <span className="text-white font-medium">{count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* User Management */}
      <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl overflow-hidden">
        <div className="p-5 border-b border-[#1a1a1d]">
          <h3 className="text-lg font-medium text-white mb-3">User Management</h3>
          <div className="flex flex-wrap gap-3">
            {/* Search */}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Search by email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="px-3 py-1.5 bg-[#04070D] border border-[#1a1a1d] rounded-lg text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-[#A6DAFF]/50 w-64"
              />
              <button
                onClick={handleSearch}
                className="px-3 py-1.5 bg-[#A6DAFF]/10 text-[#A6DAFF] rounded-lg text-sm hover:bg-[#A6DAFF]/20 transition-colors"
              >
                Search
              </button>
            </div>

            {/* Tier filter */}
            <select
              value={tierFilter}
              onChange={(e) => handleTierFilter(e.target.value as TierFilter)}
              className="px-3 py-1.5 bg-[#04070D] border border-[#1a1a1d] rounded-lg text-sm text-white focus:outline-none focus:border-[#A6DAFF]/50"
            >
              <option value="">All tiers</option>
              <option value="free">Free</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
        </div>

        {/* Users Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-[#1a1a1d]">
                <th className="px-5 py-3 font-medium">Email</th>
                <th className="px-5 py-3 font-medium">Tier</th>
                <th className="px-5 py-3 font-medium">Agents</th>
                <th className="px-5 py-3 font-medium">Requests</th>
                <th className="px-5 py-3 font-medium">Subscription</th>
                <th className="px-5 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users?.items.map((user) => (
                <tr
                  key={user.id}
                  className="border-b border-[#1a1a1d]/50 hover:bg-[#1a1a1d]/30 transition-colors"
                >
                  <td className="px-5 py-3">
                    <div className="text-white">{user.email || '—'}</div>
                    <div className="text-xs text-gray-500">{user.id.slice(0, 8)}...</div>
                  </td>
                  <td className="px-5 py-3">
                    <TierBadge tier={user.tier} />
                  </td>
                  <td className="px-5 py-3 text-gray-300">{user.agent_count}</td>
                  <td className="px-5 py-3 text-gray-300">
                    {user.requests_this_month.toLocaleString()}
                  </td>
                  <td className="px-5 py-3">
                    {user.has_subscription ? (
                      <span className="inline-flex items-center gap-1 text-green-400 text-xs">
                        <span className="w-1.5 h-1.5 bg-green-400 rounded-full" />
                        Active
                      </span>
                    ) : (
                      <span className="text-gray-500 text-xs">None</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <select
                      value={user.tier}
                      disabled={changingTier === user.id}
                      onChange={(e) => handleTierChange(user.id, e.target.value)}
                      className="px-2 py-1 bg-[#04070D] border border-[#1a1a1d] rounded text-xs text-white focus:outline-none focus:border-[#A6DAFF]/50 disabled:opacity-50"
                    >
                      <option value="free">Free</option>
                      <option value="pro">Pro</option>
                      <option value="enterprise">Enterprise</option>
                    </select>
                  </td>
                </tr>
              ))}
              {users?.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-gray-500">
                    No users found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-[#1a1a1d]">
            <span className="text-sm text-gray-400">
              Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, users?.total || 0)} of{' '}
              {users?.total || 0}
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

      {/* Stat detail drawer */}
      {selectedStat && (
        <StatDetailDrawer mode={selectedStat} onClose={() => setSelectedStat(null)} />
      )}
    </div>
  )
}

// ── Helper Components ───────────────────────────────────────────────

function StatCard({
  label,
  value,
  sublabel,
  icon,
  onClick,
}: {
  label: string
  value: string | number
  sublabel?: string
  icon: string
  onClick?: () => void
}) {
  return (
    <div
      className="bg-[#10131C] border border-[#1a1a1d] rounded-xl p-5 cursor-pointer hover:border-[#A6DAFF]/40 transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className="text-2xl font-semibold text-white mt-1">{value}</p>
          {sublabel && <p className="text-xs text-gray-500 mt-0.5">{sublabel}</p>}
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  )
}

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
