import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getAdminUserDetail, updateUserTier, type AdminUserDetail } from '../services/api/admin'
import { isApiError } from '../services/api/client'
import { useAuth } from '../hooks/useAuth'

export function AdminUserDetailPage() {
  const { user: authUser } = useAuth()
  const { id } = useParams<{ id: string }>()
  const [user, setUser] = useState<AdminUserDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [changingTier, setChangingTier] = useState(false)

  const loadUser = async () => {
    if (!id) return
    try {
      setLoading(true)
      setError(null)
      const data = await getAdminUserDetail(id)
      setUser(data)
    } catch (err) {
      if (isApiError(err) && err.status === 404) {
        setError('User not found')
      } else if (isApiError(err) && err.status === 403) {
        setError('Admin access required')
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load user')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!authUser) return
    loadUser()
  }, [authUser, id]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleTierChange = async (newTier: string) => {
    if (!user || !id) return
    if (
      !confirm(
        `Change ${user.email}'s tier to ${newTier.toUpperCase()}? This does NOT sync with Stripe.`,
      )
    )
      return

    setChangingTier(true)
    try {
      await updateUserTier(id, newTier)
      await loadUser()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update tier')
    } finally {
      setChangingTier(false)
    }
  }

  if (loading && !user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-400">Loading user profile...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Link
          to="/dashboard/admin"
          className="text-[#A6DAFF] hover:underline text-sm mb-4 inline-block"
        >
          &larr; Back to Admin
        </Link>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-red-400">
          <h3 className="font-semibold mb-1">Error</h3>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }

  if (!user) return null

  const quotaItems = [
    {
      label: 'Agents',
      used: user.agent_count,
      max: user.quotas.max_agents,
    },
    {
      label: 'Requests / month',
      used: user.requests_this_month,
      max: user.quotas.max_requests_per_month,
    },
    {
      label: 'Credentials',
      used: null, // we don't have this count yet
      max: user.quotas.max_credentials,
    },
    {
      label: 'Audit retention',
      used: null,
      max: user.quotas.audit_retention_days,
      suffix: 'days',
    },
  ]

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Back Link + Header */}
      <div>
        <Link to="/dashboard/admin" className="text-[#A6DAFF] hover:underline text-sm">
          &larr; Back to Admin
        </Link>
        <div className="flex items-start justify-between mt-3">
          <div>
            <h1 className="text-2xl font-semibold text-white flex items-center gap-3">
              {user.email || 'Unknown User'}
              <TierBadge tier={user.tier} />
              {user.role === 'admin' && (
                <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium border bg-yellow-500/10 text-yellow-400 border-yellow-500/20">
                  Admin
                </span>
              )}
            </h1>
            <p className="text-gray-400 mt-1 text-sm font-mono">{user.id}</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-400">Tier:</label>
            <select
              value={user.tier}
              disabled={changingTier}
              onChange={(e) => handleTierChange(e.target.value)}
              className="px-3 py-1.5 bg-[#04070D] border border-[#1a1a1d] rounded-lg text-sm text-white focus:outline-none focus:border-[#A6DAFF]/50 disabled:opacity-50"
            >
              <option value="free">Free</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
        </div>
      </div>

      {/* Account Info + Quota Cards */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Account Info */}
        <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-4">Account Info</h3>
          <div className="space-y-3 text-sm">
            <InfoRow label="Created" value={formatDate(user.created_at)} />
            <InfoRow label="Updated" value={formatDate(user.updated_at)} />
            <InfoRow
              label="Subscription"
              value={
                user.has_subscription ? (
                  <span className="inline-flex items-center gap-1 text-green-400">
                    <span className="w-1.5 h-1.5 bg-green-400 rounded-full" />
                    Active
                  </span>
                ) : (
                  <span className="text-gray-500">None</span>
                )
              }
            />
            <InfoRow
              label="Stripe Customer"
              value={user.stripe_customer_id || <span className="text-gray-500">N/A</span>}
            />
            <InfoRow
              label="Welcome Email"
              value={
                user.welcome_email_sent_at ? (
                  formatDate(user.welcome_email_sent_at)
                ) : (
                  <span className="text-gray-500">Not sent</span>
                )
              }
            />
            <InfoRow
              label="Follow-up Email"
              value={
                user.followup_email_sent_at ? (
                  formatDate(user.followup_email_sent_at)
                ) : (
                  <span className="text-gray-500">Not sent</span>
                )
              }
            />
          </div>
        </div>

        {/* Quota Usage */}
        <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-4">
            Tier Quotas ({user.tier.charAt(0).toUpperCase() + user.tier.slice(1)})
          </h3>
          <div className="space-y-4">
            {quotaItems.map((item) => (
              <QuotaBar key={item.label} {...item} />
            ))}
          </div>
        </div>
      </div>

      {/* Agents Table */}
      <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl overflow-hidden">
        <div className="p-5 border-b border-[#1a1a1d]">
          <h3 className="text-lg font-medium text-white">
            Agents <span className="text-gray-500 text-sm font-normal">({user.agents.length})</span>
          </h3>
        </div>
        {user.agents.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-500">No agents created</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-[#1a1a1d]">
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Keys</th>
                  <th className="px-5 py-3 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {user.agents.map((agent) => (
                  <tr
                    key={agent.id}
                    className="border-b border-[#1a1a1d]/50 hover:bg-[#1a1a1d]/30 transition-colors"
                  >
                    <td className="px-5 py-3">
                      <Link
                        to={`/dashboard/agents/${agent.id}`}
                        className="text-[#A6DAFF] hover:underline"
                      >
                        {agent.name}
                      </Link>
                      <div className="text-xs text-gray-500 font-mono">
                        {agent.id.slice(0, 8)}...
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={agent.status} />
                    </td>
                    <td className="px-5 py-3 text-gray-300">{agent.key_count}</td>
                    <td className="px-5 py-3 text-gray-400">{formatDate(agent.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl overflow-hidden">
        <div className="p-5 border-b border-[#1a1a1d]">
          <h3 className="text-lg font-medium text-white">
            Recent Activity{' '}
            <span className="text-gray-500 text-sm font-normal">
              (last {user.recent_audit_logs.length} requests)
            </span>
          </h3>
        </div>
        {user.recent_audit_logs.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-500">No activity recorded</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-[#1a1a1d]">
                  <th className="px-5 py-3 font-medium">Timestamp</th>
                  <th className="px-5 py-3 font-medium">Agent</th>
                  <th className="px-5 py-3 font-medium">Endpoint</th>
                  <th className="px-5 py-3 font-medium">Method</th>
                  <th className="px-5 py-3 font-medium">Decision</th>
                  <th className="px-5 py-3 font-medium">Latency</th>
                </tr>
              </thead>
              <tbody>
                {user.recent_audit_logs.map((entry) => (
                  <tr
                    key={entry.id}
                    className="border-b border-[#1a1a1d]/50 hover:bg-[#1a1a1d]/30 transition-colors"
                  >
                    <td className="px-5 py-3 text-gray-400 whitespace-nowrap">
                      {formatDateTime(entry.created_at)}
                    </td>
                    <td className="px-5 py-3 text-gray-300">
                      {entry.agent_name || (
                        <span className="text-gray-500 font-mono text-xs">
                          {entry.agent_id.slice(0, 8)}...
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <span className="text-gray-300 font-mono text-xs">{entry.endpoint}</span>
                    </td>
                    <td className="px-5 py-3">
                      <MethodBadge method={entry.method} />
                    </td>
                    <td className="px-5 py-3">
                      <DecisionBadge decision={entry.decision} />
                    </td>
                    <td className="px-5 py-3 text-gray-400">
                      {entry.latency_ms != null ? `${entry.latency_ms}ms` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Helper Components ───────────────────────────────────────────────

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-400">{label}</span>
      <span className="text-white">{value}</span>
    </div>
  )
}

function QuotaBar({
  label,
  used,
  max,
  suffix,
}: {
  label: string
  used: number | null
  max: number
  suffix?: string
}) {
  const isUnlimited = max === -1
  const displayMax = isUnlimited
    ? 'Unlimited'
    : `${max.toLocaleString()}${suffix ? ` ${suffix}` : ''}`

  if (used == null) {
    // Display-only (no progress bar)
    return (
      <div>
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-400">{label}</span>
          <span className="text-white">{displayMax}</span>
        </div>
      </div>
    )
  }

  const pct = isUnlimited ? 0 : max > 0 ? Math.min((used / max) * 100, 100) : 0
  const isHigh = pct > 80

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-white">
          {used.toLocaleString()} / {displayMax}
        </span>
      </div>
      {!isUnlimited && (
        <div className="h-1.5 bg-[#1a1a1d] rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${isHigh ? 'bg-red-500' : 'bg-[#A6DAFF]'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
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

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'text-green-400',
    suspended: 'text-yellow-400',
    revoked: 'text-red-400',
  }
  return (
    <span className={`inline-flex items-center gap-1 text-xs ${colors[status] || 'text-gray-400'}`}>
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          status === 'active'
            ? 'bg-green-400'
            : status === 'suspended'
              ? 'bg-yellow-400'
              : 'bg-red-400'
        }`}
      />
      {status.charAt(0).toUpperCase() + status.slice(1)}
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

function DecisionBadge({ decision }: { decision: string }) {
  const map: Record<string, { color: string; dot: string }> = {
    allow: { color: 'text-green-400', dot: 'bg-green-400' },
    deny: { color: 'text-red-400', dot: 'bg-red-400' },
    error: { color: 'text-yellow-400', dot: 'bg-yellow-400' },
  }
  const style = map[decision] || map.error
  return (
    <span className={`inline-flex items-center gap-1 text-xs ${style.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {decision.charAt(0).toUpperCase() + decision.slice(1)}
    </span>
  )
}

// ── Formatters ──────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
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
