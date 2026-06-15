import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { getPendingCount } from '../services/api/approvals'
import { getShadowAgentStats } from '../services/api/shadow'
import { getQAHasPending } from '../services/api/qa'
import { useAuth } from '../hooks/useAuth'

type Tone = 'warning' | 'danger' | 'brand'

interface AttentionItem {
  key: string
  label: string
  value: string
  to: string
  cta: string
  tone: Tone
  icon: ReactNode
}

const toneBorder: Record<Tone, string> = {
  warning: 'border-l-warning',
  danger: 'border-l-danger',
  brand: 'border-l-brand',
}

const toneText: Record<Tone, string> = {
  warning: 'text-warning',
  danger: 'text-danger',
  brand: 'text-brand',
}

/* ── Small inline icons (20×20) ─────────────────────────────────── */
const icons = {
  clock: (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z"
        clipRule="evenodd"
      />
    </svg>
  ),
  eye: (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
      <path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
      <path
        fillRule="evenodd"
        d="M.664 10.59a1.651 1.651 0 010-1.186A10.004 10.004 0 0110 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0110 17c-4.257 0-7.893-2.66-9.336-6.41zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
        clipRule="evenodd"
      />
    </svg>
  ),
  signature: (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
      <path
        fillRule="evenodd"
        d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
        clipRule="evenodd"
      />
    </svg>
  ),
}

export function AttentionPanel() {
  const { user } = useAuth()
  const [items, setItems] = useState<AttentionItem[] | null>(null)

  useEffect(() => {
    // Wait for auth to be ready before fetching (matches useDashboardData)
    if (!user) return

    let cancelled = false
    async function load() {
      const [approvals, shadow, qa] = await Promise.all([
        getPendingCount().catch(() => null),
        getShadowAgentStats().catch(() => null),
        getQAHasPending().catch(() => null),
      ])
      if (cancelled) return
      const next: AttentionItem[] = []
      if (approvals && approvals.count > 0) {
        next.push({
          key: 'approvals',
          tone: 'warning',
          label: 'Approvals',
          value: `${approvals.count} pending`,
          to: '/dashboard/approvals',
          cta: 'Review',
          icon: icons.clock,
        })
      }
      if (shadow && shadow.total_shadow_agents > 0) {
        next.push({
          key: 'shadow',
          tone: 'danger',
          label: 'Shadow agents',
          value: `${shadow.total_shadow_agents} detected`,
          to: '/dashboard/shadow-agents',
          cta: 'Investigate',
          icon: icons.eye,
        })
      }
      if (qa && qa.has_pending) {
        next.push({
          key: 'qa',
          tone: 'brand',
          label: 'QA acceptance',
          value: 'Awaiting sign-off',
          to: '/dashboard/qa',
          cta: 'Sign off',
          icon: icons.signature,
        })
      }
      setItems(next)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [user])

  // Loading
  if (items === null) {
    return (
      <section>
        <h2 className="mb-3 text-lg font-medium text-ink">Needs your attention</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-elevated" />
          ))}
        </div>
      </section>
    )
  }

  // All clear
  if (items.length === 0) {
    return (
      <section>
        <div className="flex items-center gap-3 rounded-xl border border-line bg-surface p-4">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-success-soft text-success">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
              <path
                fillRule="evenodd"
                d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                clipRule="evenodd"
              />
            </svg>
          </span>
          <div>
            <p className="text-sm font-medium text-ink">You're all caught up</p>
            <p className="text-sm text-muted">Nothing needs your attention right now.</p>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section>
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-lg font-medium text-ink">Needs your attention</h2>
        <span className="text-sm text-subtle">
          {items.length} {items.length === 1 ? 'item' : 'items'}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {items.map((item) => (
          <Link
            key={item.key}
            to={item.to}
            className={`group rounded-xl border border-l-2 border-line bg-surface p-4 transition-colors hover:border-line-strong ${toneBorder[item.tone]}`}
          >
            <div className={`flex items-center gap-2 text-xs ${toneText[item.tone]}`}>
              {item.icon}
              {item.label}
            </div>
            <p className="mt-2 text-xl font-medium text-ink">{item.value}</p>
            <span className="mt-2 inline-flex items-center gap-1 text-xs text-brand">
              {item.cta}
              <span aria-hidden="true" className="transition-transform group-hover:translate-x-0.5">
                &rarr;
              </span>
            </span>
          </Link>
        ))}
      </div>
    </section>
  )
}
