import { useState, useEffect } from 'react'
import {
  getUsageSummary,
  getUsageAggregation,
  getBillingStatus,
  createCheckoutSession,
  createPortalSession,
  type UsageSummary,
  type UsageAggregation,
  type BillingStatus,
  type QuotaUsage,
} from '../services/api/billing'

// ── Helpers ──────────────────────────────────────────────────────

function tierLabel(tier: string): string {
  return tier.charAt(0).toUpperCase() + tier.slice(1)
}

function tierColor(tier: string): string {
  switch (tier) {
    case 'pro':
      return 'text-[#A6DAFF]'
    case 'business':
      return 'text-blue-400'
    case 'enterprise':
      return 'text-purple-400'
    default:
      return 'text-gray-400'
  }
}

function tierBadgeClasses(tier: string): string {
  switch (tier) {
    case 'pro':
      return 'bg-[#A6DAFF]/10 text-[#A6DAFF] border-[#A6DAFF]/20'
    case 'business':
      return 'bg-blue-500/10 text-blue-400 border-blue-500/20'
    case 'enterprise':
      return 'bg-purple-500/10 text-purple-400 border-purple-500/20'
    default:
      return 'bg-gray-500/10 text-gray-400 border-gray-500/20'
  }
}

function formatLimit(q: QuotaUsage): string {
  return q.unlimited ? 'Unlimited' : (q.limit?.toLocaleString() ?? '0')
}

function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function progressColor(pct: number): string {
  if (pct >= 90) return 'bg-red-500'
  if (pct >= 70) return 'bg-yellow-500'
  return 'bg-[#A6DAFF]'
}

function subStatusBadge(status: string): string {
  switch (status) {
    case 'active':
    case 'trialing':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
    case 'past_due':
      return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
    case 'canceled':
    case 'unpaid':
      return 'bg-red-500/10 text-red-400 border-red-500/20'
    default:
      return 'bg-gray-500/10 text-gray-400 border-gray-500/20'
  }
}

// ── Quota Progress Bar ──────────────────────────────────────────

function QuotaBar({
  label,
  quota,
  icon,
}: {
  label: string
  quota: QuotaUsage
  icon: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-gray-400">{icon}</span>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-400">{label}</p>
        </div>
        <p className="text-xs text-gray-500">
          {quota.current.toLocaleString()} / {formatLimit(quota)}
        </p>
      </div>
      <div className="mt-3 h-2 rounded-full bg-[#1a1a1d]">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            quota.unlimited ? 'bg-[#A6DAFF]/30' : progressColor(quota.percentage)
          }`}
          style={{ width: `${quota.unlimited ? 0 : Math.min(quota.percentage, 100)}%` }}
        />
      </div>
      <p className="mt-1.5 text-right text-xs text-gray-500">
        {quota.unlimited ? 'Unlimited' : `${quota.percentage.toFixed(1)}% used`}
      </p>
    </div>
  )
}

// ── Daily Usage Chart (simple bar chart) ────────────────────────

function DailyChart({ daily }: { daily: UsageAggregation['daily'] }) {
  if (daily.length === 0) return null
  const maxRequests = Math.max(...daily.map((d) => d.total_requests), 1)

  return (
    <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
      <h3 className="text-sm font-medium text-white">Daily Requests</h3>
      <p className="mt-1 text-xs text-gray-500">Current billing period</p>
      <div className="mt-4 flex items-end gap-[2px] h-32">
        {daily.map((d) => {
          const height = (d.total_requests / maxRequests) * 100
          const allowedPct = d.total_requests > 0 ? (d.allowed / d.total_requests) * height : 0
          const deniedPct = d.total_requests > 0 ? (d.denied / d.total_requests) * height : 0
          const errorPct = d.total_requests > 0 ? (d.errors / d.total_requests) * height : 0

          return (
            <div
              key={d.date}
              className="flex-1 flex flex-col justify-end group relative"
              title={`${d.date}: ${d.total_requests} requests (${d.allowed} allowed, ${d.denied} denied)`}
            >
              {/* Tooltip */}
              <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover:block z-10">
                <div className="rounded-lg bg-[#1a1a1d] border border-[#2a2a2d] px-2.5 py-1.5 text-[10px] text-gray-300 whitespace-nowrap shadow-lg">
                  <p className="font-medium text-white">{d.date}</p>
                  <p>{d.total_requests} total</p>
                  {d.denied > 0 && <p className="text-red-400">{d.denied} denied</p>}
                </div>
              </div>
              {/* Stacked bar */}
              <div
                className="w-full rounded-t-sm bg-red-500/80 transition-all"
                style={{ height: `${errorPct}%` }}
              />
              <div
                className="w-full bg-red-400/60 transition-all"
                style={{ height: `${deniedPct}%` }}
              />
              <div
                className="w-full rounded-t-sm bg-[#A6DAFF] transition-all hover:bg-[#A6DAFF]/80"
                style={{ height: `${allowedPct}%`, minHeight: d.total_requests > 0 ? '2px' : '0' }}
              />
            </div>
          )
        })}
      </div>
      {/* Date axis labels */}
      <div className="mt-2 flex justify-between text-[9px] text-gray-600">
        <span>{daily[0]?.date?.slice(5)}</span>
        <span>{daily[daily.length - 1]?.date?.slice(5)}</span>
      </div>
      {/* Legend */}
      <div className="mt-3 flex items-center gap-4 text-[10px] text-gray-500">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-[#A6DAFF]" /> Allowed
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-red-400/60" /> Denied
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-red-500/80" /> Errors
        </span>
      </div>
    </div>
  )
}

// ── Agent Breakdown Table ───────────────────────────────────────

function AgentBreakdown({ agents }: { agents: UsageAggregation['by_agent'] }) {
  if (agents.length === 0) {
    return (
      <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
        <h3 className="text-sm font-medium text-white">Per-Agent Breakdown</h3>
        <p className="mt-4 text-center text-sm text-gray-500">
          No agent activity this billing period
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
      <h3 className="text-sm font-medium text-white">Per-Agent Breakdown</h3>
      <p className="mt-1 text-xs text-gray-500">Current billing period</p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1a1a1d]">
              <th className="pb-2 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                Agent
              </th>
              <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-gray-400">
                Requests
              </th>
              <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-gray-400">
                Allowed
              </th>
              <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-gray-400">
                Denied
              </th>
              <th className="pb-2 text-right text-xs font-medium uppercase tracking-wider text-gray-400">
                Last Active
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1a1a1d]">
            {agents.map((a) => (
              <tr key={a.agent_id} className="hover:bg-[#1a1a1d]/30 transition-colors">
                <td className="py-2.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        a.agent_status === 'active'
                          ? 'bg-emerald-400'
                          : a.agent_status === 'suspended'
                            ? 'bg-yellow-400'
                            : 'bg-red-400'
                      }`}
                    />
                    <span className="text-sm text-white">{a.agent_name}</span>
                  </div>
                </td>
                <td className="py-2.5 text-right font-mono text-sm text-gray-300">
                  {a.total_requests.toLocaleString()}
                </td>
                <td className="py-2.5 text-right font-mono text-sm text-emerald-400">
                  {a.allowed.toLocaleString()}
                </td>
                <td className="py-2.5 text-right font-mono text-sm text-red-400">
                  {a.denied > 0 ? a.denied.toLocaleString() : '—'}
                </td>
                <td className="py-2.5 text-right text-xs text-gray-500">
                  {a.last_active
                    ? new Date(a.last_active).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                      })
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tier Comparison ────────────────────────────────────────────

function TierComparison({ currentTier }: { currentTier: string }) {
  const tiers = [
    {
      name: 'Free',
      key: 'free',
      price: '$0',
      features: ['5 agents', '2,000 requests/mo', '1 credential', '30-day audit retention'],
    },
    {
      name: 'Pro',
      key: 'pro',
      price: '$79/mo',
      features: [
        '50 agents',
        '75,000 requests/mo',
        '10 credentials',
        '90-day audit retention',
        'Basic SSO',
      ],
    },
    {
      name: 'Business',
      key: 'business',
      price: '$299/mo',
      features: [
        '200 agents',
        '500,000 requests/mo',
        '50 credentials',
        '1-year audit retention',
        'Priority support',
        'SAML / SCIM',
      ],
    },
    {
      name: 'Enterprise',
      key: 'enterprise',
      price: 'Custom',
      features: [
        'Unlimited agents',
        'Unlimited requests',
        'Unlimited credentials',
        'Unlimited audit retention',
        'Dedicated support + SLA',
        'On-premise / VPC',
      ],
    },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {tiers.map((t) => {
        const isCurrent = t.key === currentTier

        return (
          <div
            key={t.key}
            className={`rounded-xl border p-5 transition-colors ${
              isCurrent
                ? 'border-[#A6DAFF]/40 bg-[#A6DAFF]/5'
                : 'border-[#1a1a1d] bg-[#10131C]/80 hover:border-[#2a2a2d]'
            }`}
          >
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-white">{t.name}</h4>
              {isCurrent && (
                <span className="rounded-full border border-[#A6DAFF]/30 bg-[#A6DAFF]/10 px-2 py-0.5 text-[10px] font-medium text-[#A6DAFF]">
                  Current
                </span>
              )}
            </div>
            <p className="mt-1 text-2xl font-bold text-white">{t.price}</p>
            <ul className="mt-4 space-y-2">
              {t.features.map((f) => (
                <li key={f} className="flex items-center gap-2 text-xs text-gray-400">
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke={isCurrent ? '#A6DAFF' : '#10b981'}
                    strokeWidth="2"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
  )
}

// ── Main Page Component ─────────────────────────────────────────

export function UsageBillingPage() {
  const [usage, setUsage] = useState<UsageSummary | null>(null)
  const [aggregation, setAggregation] = useState<UsageAggregation | null>(null)
  const [billing, setBilling] = useState<BillingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [portalLoading, setPortalLoading] = useState(false)

  // ── Load data ───────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)

      try {
        const [usageData, aggData, billingData] = await Promise.allSettled([
          getUsageSummary(),
          getUsageAggregation(),
          getBillingStatus(),
        ])

        if (cancelled) return

        if (usageData.status === 'fulfilled') setUsage(usageData.value)
        if (aggData.status === 'fulfilled') setAggregation(aggData.value)
        if (billingData.status === 'fulfilled') setBilling(billingData.value)

        // Show error only if usage (primary data) failed
        if (usageData.status === 'rejected') {
          setError('Unable to load usage data. Check your API key.')
        }
      } catch {
        if (!cancelled) setError('Failed to load billing data')
      }

      if (!cancelled) setLoading(false)
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  // ── Upgrade to Pro ──────────────────────────────────────────

  const handleUpgrade = async () => {
    setCheckoutLoading(true)
    try {
      const { checkout_url } = await createCheckoutSession('pro')
      window.location.href = checkout_url
    } catch (err) {
      const message =
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: string }).message)
          : 'Failed to create checkout session'
      setError(message)
      setCheckoutLoading(false)
    }
  }

  // ── Manage Subscription ─────────────────────────────────────

  const handleManageSubscription = async () => {
    setPortalLoading(true)
    try {
      const { portal_url } = await createPortalSession()
      window.location.href = portal_url
    } catch (err) {
      const message =
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: string }).message)
          : 'Failed to open billing portal'
      setError(message)
      setPortalLoading(false)
    }
  }

  // ── Loading state ───────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 animate-bounce rounded-full bg-[#A6DAFF]" />
          <div
            className="h-2 w-2 animate-bounce rounded-full bg-[#A6DAFF]"
            style={{ animationDelay: '0.15s' }}
          />
          <div
            className="h-2 w-2 animate-bounce rounded-full bg-[#A6DAFF]"
            style={{ animationDelay: '0.3s' }}
          />
        </div>
      </div>
    )
  }

  const currentTier = usage?.tier ?? billing?.tier ?? 'free'

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Usage & Billing</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-[#71717a]">
            Monitor your resource usage and manage your subscription
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium ${tierBadgeClasses(currentTier)}`}
          >
            {tierLabel(currentTier)} Plan
          </span>
          {currentTier === 'free' && (
            <button
              onClick={handleUpgrade}
              disabled={checkoutLoading}
              className="rounded-lg bg-[#A6DAFF] px-4 py-2 text-sm font-medium text-black hover:bg-[#A6DAFF]/90 transition-colors disabled:opacity-50"
            >
              {checkoutLoading ? 'Redirecting...' : 'Upgrade to Pro'}
            </button>
          )}
          {billing?.has_subscription && (
            <button
              onClick={handleManageSubscription}
              disabled={portalLoading}
              className="rounded-lg border border-[#1a1a1d] bg-[#10131C] px-4 py-2 text-sm text-gray-300 hover:border-[#A6DAFF]/30 hover:text-white transition-colors disabled:opacity-50"
            >
              {portalLoading ? 'Opening...' : 'Manage Subscription'}
            </button>
          )}
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-4">
          <div className="flex items-center gap-2">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#f87171"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p className="text-sm text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Subscription status card (if subscribed) */}
      {billing?.subscription && (
        <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-medium text-white">Subscription</h3>
                <span
                  className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${subStatusBadge(billing.subscription.status)}`}
                >
                  {billing.subscription.status}
                </span>
                {billing.subscription.cancel_at_period_end && (
                  <span className="rounded-full border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 text-xs font-medium text-yellow-400">
                    Cancels at period end
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Current period: {formatDate(billing.subscription.current_period_start)} –{' '}
                {formatDate(billing.subscription.current_period_end)}
              </p>
            </div>
            <p className="text-xs text-gray-500 font-mono">{billing.subscription.id}</p>
          </div>
        </div>
      )}

      {/* Quota usage cards */}
      {usage && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <QuotaBar
            label="Agents"
            quota={usage.agents}
            icon={
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M10 9a3 3 0 100-6 3 3 0 000 6zM6 8a2 2 0 11-4 0 2 2 0 014 0zM1.49 15.326a.78.78 0 01-.358-.442 3 3 0 014.308-3.516 6.484 6.484 0 00-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 01-2.07-.655zM16.44 15.98a4.97 4.97 0 002.07-.654.78.78 0 00.357-.442 3 3 0 00-4.308-3.517 6.484 6.484 0 011.907 3.96 2.32 2.32 0 01-.026.654zM18 8a2 2 0 11-4 0 2 2 0 014 0zM5.304 16.19a.844.844 0 01-.277-.71 5 5 0 019.947 0 .843.843 0 01-.277.71A6.975 6.975 0 0110 18a6.974 6.974 0 01-4.696-1.81z" />
              </svg>
            }
          />
          <QuotaBar
            label="Monthly Requests"
            quota={usage.requests_this_month}
            icon={
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H4.28a.75.75 0 00-.75.75v3.955a.75.75 0 001.5 0v-2.134l.312.312a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V3.216a.75.75 0 00-1.5 0v2.134l-.312-.312A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h3.955a.75.75 0 00.53-.219z" />
              </svg>
            }
          />
          <QuotaBar
            label="API Keys"
            quota={usage.active_keys}
            icon={
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path
                  fillRule="evenodd"
                  d="M8 7a5 5 0 113.61 4.804l-1.903 1.903A.75.75 0 019.17 14H8v1.17a.75.75 0 01-.22.53l-.5.5a.75.75 0 01-.531.22H5.672a.75.75 0 01-.53-.22l-.5-.5a.75.75 0 01-.22-.53V13.59a.75.75 0 01.22-.53L8.196 9.54A5.003 5.003 0 018 7zm5-3a.75.75 0 000 1.5A1.5 1.5 0 0114.5 7 .75.75 0 0016 7a3 3 0 00-3-3z"
                  clipRule="evenodd"
                />
              </svg>
            }
          />
          <QuotaBar
            label="Credentials"
            quota={usage.credentials}
            icon={
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path
                  fillRule="evenodd"
                  d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
                  clipRule="evenodd"
                />
              </svg>
            }
          />
        </div>
      )}

      {/* Billing period summary */}
      {aggregation?.billing_period && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
            <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Billing Period
            </p>
            <p className="mt-2 text-lg font-bold text-white">
              {aggregation.billing_period.period_start.slice(5)} –{' '}
              {aggregation.billing_period.period_end.slice(5)}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              {usage ? `${usage.agents.current} active` : ''}
              {usage && aggregation.billing_period.agents_seen > 0 ? ' · ' : ''}
              {aggregation.billing_period.agents_seen > 0
                ? `${aggregation.billing_period.agents_seen} seen in logs`
                : 'No agents seen in logs'}
            </p>
          </div>
          <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
            <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Total Requests
            </p>
            <p className="mt-2 text-2xl font-bold text-white">
              {aggregation.billing_period.total_requests.toLocaleString()}
            </p>
            <div className="mt-1 flex items-center gap-2 text-xs">
              <span className="text-emerald-400">
                {aggregation.billing_period.allowed.toLocaleString()} allowed
              </span>
              {aggregation.billing_period.denied > 0 && (
                <span className="text-red-400">
                  {aggregation.billing_period.denied.toLocaleString()} denied
                </span>
              )}
            </div>
          </div>
          <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
            <p className="text-xs font-medium uppercase tracking-wider text-gray-400">Peak Daily</p>
            <p className="mt-2 text-2xl font-bold text-white">
              {aggregation.billing_period.peak_daily_requests.toLocaleString()}
            </p>
            <p className="mt-1 text-xs text-gray-500">requests in a single day</p>
          </div>
          <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
            <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Daily Average
            </p>
            <p className="mt-2 text-2xl font-bold text-white">
              {aggregation.billing_period.avg_daily_requests.toFixed(0)}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              {aggregation.previous_period
                ? `Previous: ${aggregation.previous_period.avg_daily_requests.toFixed(0)}/day`
                : 'No previous period data'}
            </p>
          </div>
        </div>
      )}

      {/* Daily chart */}
      {aggregation && <DailyChart daily={aggregation.daily} />}

      {/* Per-agent breakdown */}
      {aggregation && <AgentBreakdown agents={aggregation.by_agent} />}

      {/* Tier comparison */}
      <div>
        <h2 className="text-lg font-semibold text-white">Plans</h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-[#71717a]">
          Compare available plans and their limits
        </p>
        <div className="mt-4">
          <TierComparison currentTier={currentTier} />
        </div>
      </div>

      {/* Audit retention info */}
      {usage && (
        <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 backdrop-blur-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-white">Audit Log Retention</h3>
              <p className="mt-1 text-xs text-gray-500">
                {usage.audit_retention_days === -1
                  ? 'Unlimited retention — all audit entries are preserved indefinitely'
                  : `Audit entries are retained for ${usage.audit_retention_days} days`}
              </p>
            </div>
            <span className={`text-2xl font-bold ${tierColor(currentTier)}`}>
              {usage.audit_retention_days === -1 ? '∞' : `${usage.audit_retention_days}d`}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
