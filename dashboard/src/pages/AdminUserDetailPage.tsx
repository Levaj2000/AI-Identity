import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getAdminUserDetail, updateUserTier, type AdminUserDetail } from '../services/api/admin'
import { isApiError } from '../services/api/client'

export function AdminUserDetailPage() {
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
    loadUser()
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

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
        <div className="text-muted">Loading user profile...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Link
          to="/dashboard/admin"
          className="text-brand hover:underline text-sm mb-4 inline-block"
        >
          &larr; Back to Admin
        </Link>
        <div className="bg-danger-soft border border-danger rounded-xl p-6 text-danger">
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
        <Link to="/dashboard/admin" className="text-brand hover:underline text-sm">
          &larr; Back to Admin
        </Link>
        <div className="flex items-start justify-between mt-3">
          <div>
            <h1 className="text-2xl font-semibold text-ink flex items-center gap-3">
              {user.email || 'Unknown User'}
              <TierBadge tier={user.tier} />
              {user.role === 'admin' && (
                <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium border bg-warning-soft text-warning border-warning">
                  Admin
                </span>
              )}
            </h1>
            <p className="text-muted mt-1 text-sm font-mono">{user.id}</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-muted">Tier:</label>
            <select
              value={user.tier}
              disabled={changingTier}
              onChange={(e) => handleTierChange(e.target.value)}
              className="px-3 py-1.5 bg-inset border border-line rounded-lg text-sm text-ink focus:outline-none focus:border-brand/50 disabled:opacity-50"
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
        <div className="bg-surface border border-line rounded-xl p-5">
          <h3 className="text-sm font-medium text-muted mb-4">Account Info</h3>
          <div className="space-y-3 text-sm">
            <InfoRow label="Created" value={formatDate(user.created_at)} />
            <InfoRow label="Updated" value={formatDate(user.updated_at)} />
            <InfoRow
              label="Subscription"
              value={
                user.has_subscription ? (
                  <span className="inline-flex items-center gap-1 text-success">
                    <span className="w-1.5 h-1.5 bg-success rounded-full" />
                    Active
                  </span>
                ) : (
                  <span className="text-subtle">None</span>
                )
              }
            />
            <InfoRow
              label="Stripe Customer"
              value={user.stripe_customer_id || <span className="text-subtle">N/A</span>}
            />
            <InfoRow
              label="Welcome Email"
              value={
                user.welcome_email_sent_at ? (
                  formatDate(user.welcome_email_sent_at)
                ) : (
                  <span className="text-subtle">Not sent</span>
                )
              }
            />
            <InfoRow
              label="Follow-up Email"
              value={
                user.followup_email_sent_at ? (
                  formatDate(user.followup_email_sent_at)
                ) : (
                  <span className="text-subtle">Not sent</span>
                )
              }
            />
          </div>
        </div>

        {/* Quota Usage */}
        <div className="bg-surface border border-line rounded-xl p-5">
          <h3 className="text-sm font-medium text-muted mb-4">
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
      <div className="bg-surface border border-line rounded-xl overflow-hidden">
        <div className="p-5 border-b border-line">
          <h3 className="text-lg font-medium text-ink">
            Agents <span className="text-subtle text-sm font-normal">({user.agents.length})</span>
          </h3>
        </div>
        {user.agents.length === 0 ? (
          <div className="px-5 py-8 text-center text-subtle">No agents created</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted border-b border-line">
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
                    className="border-b border-line hover:bg-elevated transition-colors"
                  >
                    <td className="px-5 py-3">
                      <Link
                        to={`/dashboard/agents/${agent.id}`}
                        className="text-brand hover:underline"
                      >
                        {agent.name}
                      </Link>
                      <div className="text-xs text-subtle font-mono">{agent.id.slice(0, 8)}...</div>
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={agent.status} />
                    </td>
                    <td className="px-5 py-3 text-muted">{agent.key_count}</td>
                    <td className="px-5 py-3 text-muted">{formatDate(agent.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div className="bg-surface border border-line rounded-xl overflow-hidden">
        <div className="p-5 border-b border-line">
          <h3 className="text-lg font-medium text-ink">
            Recent Activity{' '}
            <span className="text-subtle text-sm font-normal">
              (last {user.recent_audit_logs.length} requests)
            </span>
          </h3>
        </div>
        {user.recent_audit_logs.length === 0 ? (
          <div className="px-5 py-8 text-center text-subtle">No activity recorded</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted border-b border-line">
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
                    className="border-b border-line hover:bg-elevated transition-colors"
                  >
                    <td className="px-5 py-3 text-muted whitespace-nowrap">
                      {formatDateTime(entry.created_at)}
                    </td>
                    <td className="px-5 py-3 text-muted">
                      {entry.agent_name || (
                        <span className="text-subtle font-mono text-xs">
                          {entry.agent_id.slice(0, 8)}...
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <span className="text-muted font-mono text-xs">{entry.endpoint}</span>
                    </td>
                    <td className="px-5 py-3">
                      <MethodBadge method={entry.method} />
                    </td>
                    <td className="px-5 py-3">
                      <DecisionBadge decision={entry.decision} />
                    </td>
                    <td className="px-5 py-3 text-muted">
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
      <span className="text-muted">{label}</span>
      <span className="text-ink">{value}</span>
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
          <span className="text-muted">{label}</span>
          <span className="text-ink">{displayMax}</span>
        </div>
      </div>
    )
  }

  const pct = isUnlimited ? 0 : max > 0 ? Math.min((used / max) * 100, 100) : 0
  const isHigh = pct > 80

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-muted">{label}</span>
        <span className="text-ink">
          {used.toLocaleString()} / {displayMax}
        </span>
      </div>
      {!isUnlimited && (
        <div className="h-1.5 bg-elevated rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${isHigh ? 'bg-danger' : 'bg-brand'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
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

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'text-success',
    suspended: 'text-warning',
    revoked: 'text-danger',
  }
  return (
    <span className={`inline-flex items-center gap-1 text-xs ${colors[status] || 'text-muted'}`}>
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          status === 'active' ? 'bg-success' : status === 'suspended' ? 'bg-warning' : 'bg-danger'
        }`}
      />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: 'text-success',
    POST: 'text-brand',
    PUT: 'text-warning',
    PATCH: 'text-warning',
    DELETE: 'text-danger',
  }
  return (
    <span className={`font-mono text-xs font-medium ${colors[method] || 'text-muted'}`}>
      {method}
    </span>
  )
}

function DecisionBadge({ decision }: { decision: string }) {
  const map: Record<string, { color: string; dot: string }> = {
    allow: { color: 'text-success', dot: 'bg-success' },
    deny: { color: 'text-danger', dot: 'bg-danger' },
    error: { color: 'text-warning', dot: 'bg-warning' },
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
