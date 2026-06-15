import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
        <h2 className="text-2xl font-semibold text-ink mb-2">Admin Access Required</h2>
        <p className="text-muted">
          Your account does not have admin privileges. Contact the platform owner for access.
        </p>
      </div>
    )
  }

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-muted">Loading admin dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-danger-soft border border-danger rounded-xl p-6 text-danger">
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
        <h1 className="text-2xl font-semibold text-ink">Admin Dashboard</h1>
        <p className="text-muted mt-1">Platform overview and user management</p>
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
        <div className="bg-surface border border-line rounded-xl p-5">
          <h3 className="text-sm font-medium text-muted mb-3">Users by Tier</h3>
          <div className="flex gap-4">
            {['free', 'pro', 'enterprise'].map((tier) => (
              <div key={tier} className="flex items-center gap-2">
                <TierBadge tier={tier} />
                <span className="text-ink font-medium">{stats.users_by_tier[tier] || 0}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Table Counts */}
      {health && (
        <div className="bg-surface border border-line rounded-xl p-5">
          <h3 className="text-sm font-medium text-muted mb-3">Database Tables</h3>
          <div className="flex gap-6">
            {Object.entries(health.table_counts).map(([table, count]) => (
              <div key={table} className="text-sm">
                <span className="text-muted">{table}:</span>{' '}
                <span className="text-ink font-medium">{count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* User Management */}
      <div className="bg-surface border border-line rounded-xl overflow-hidden">
        <div className="p-5 border-b border-line">
          <h3 className="text-lg font-medium text-ink mb-3">User Management</h3>
          <div className="flex flex-wrap gap-3">
            {/* Search */}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Search by email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="px-3 py-1.5 bg-inset border border-line rounded-lg text-sm text-ink placeholder:text-faint focus:outline-none focus:border-brand/50 w-64"
              />
              <button
                onClick={handleSearch}
                className="px-3 py-1.5 bg-brand-soft text-brand rounded-lg text-sm hover:bg-brand-soft transition-colors"
              >
                Search
              </button>
            </div>

            {/* Tier filter */}
            <select
              value={tierFilter}
              onChange={(e) => handleTierFilter(e.target.value as TierFilter)}
              className="px-3 py-1.5 bg-inset border border-line rounded-lg text-sm text-ink focus:outline-none focus:border-brand/50"
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
              <tr className="text-left text-muted border-b border-line">
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
                  className="border-b border-line hover:bg-elevated transition-colors"
                >
                  <td className="px-5 py-3">
                    <Link
                      to={`/dashboard/admin/users/${user.id}`}
                      className="text-brand hover:underline"
                    >
                      {user.email || '—'}
                    </Link>
                    <div className="text-xs text-subtle">{user.id.slice(0, 8)}...</div>
                  </td>
                  <td className="px-5 py-3">
                    <TierBadge tier={user.tier} />
                  </td>
                  <td className="px-5 py-3 text-muted">{user.agent_count}</td>
                  <td className="px-5 py-3 text-muted">
                    {user.requests_this_month.toLocaleString()}
                  </td>
                  <td className="px-5 py-3">
                    {user.has_subscription ? (
                      <span className="inline-flex items-center gap-1 text-success text-xs">
                        <span className="w-1.5 h-1.5 bg-success rounded-full" />
                        Active
                      </span>
                    ) : (
                      <span className="text-subtle text-xs">None</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <select
                      value={user.tier}
                      disabled={changingTier === user.id}
                      onChange={(e) => handleTierChange(user.id, e.target.value)}
                      className="px-2 py-1 bg-inset border border-line rounded text-xs text-ink focus:outline-none focus:border-brand/50 disabled:opacity-50"
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
                  <td colSpan={6} className="px-5 py-8 text-center text-subtle">
                    No users found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-line">
            <span className="text-sm text-muted">
              Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, users?.total || 0)} of{' '}
              {users?.total || 0}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 0}
                className="px-3 py-1 text-sm rounded border border-line text-muted hover:bg-elevated disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages - 1}
                className="px-3 py-1 text-sm rounded border border-line text-muted hover:bg-elevated disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
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
      className="bg-surface border border-line rounded-xl p-5 cursor-pointer hover:border-brand/40 transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted">{label}</p>
          <p className="text-2xl font-semibold text-ink mt-1">{value}</p>
          {sublabel && <p className="text-xs text-subtle mt-0.5">{sublabel}</p>}
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  )
}

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    free: 'bg-elevated text-muted border-line',
    pro: 'bg-brand-soft text-brand border-brand/20',
    enterprise: 'bg-ai-soft text-ai border-ai',
  }
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium border ${colors[tier] || colors.free}`}
    >
      {tier.charAt(0).toUpperCase() + tier.slice(1)}
    </span>
  )
}
