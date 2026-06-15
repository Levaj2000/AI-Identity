import { Link } from 'react-router-dom'
import { ENDPOINTS } from '../config/api'
import { useDashboardData } from '../hooks/useDashboardData'
import { AttentionPanel } from '../components/AttentionPanel'
import { MetricStrip } from '../components/MetricStrip'
import { RecentActivity } from '../components/RecentActivity'
import { GettingStarted } from '../components/GettingStarted'
import { SystemStatusBanner } from '../components/SystemStatusBanner'
import { RequestVolumeChart } from '../components/RequestVolumeChart'
import { AgentHealthGrid } from '../components/AgentHealthGrid'
import { QuickStartBar } from '../components/QuickStartBar'

export function OverviewPage() {
  const { stats, recentAgents, isLoading, error, isEmpty } = useDashboardData()

  // Error state — short-circuits the page
  if (error) {
    return (
      <div className="rounded-xl border border-danger bg-danger-soft p-6">
        <h2 className="mb-1 font-medium text-danger">
          {error.status === 401 ? 'Authentication failed' : 'Unable to load dashboard'}
        </h2>
        <p className="text-sm text-danger">
          {error.status === 401
            ? 'Your session may have expired. Try signing out and back in.'
            : error.message}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Action-first: what needs you, before the numbers */}
      <AttentionPanel />

      {isLoading ? (
        <div className="space-y-8">
          <div className="h-16 animate-pulse rounded-xl bg-elevated" />
          <div className="h-64 animate-pulse rounded-xl bg-elevated" />
        </div>
      ) : (
        <>
          {/* Demoted at-a-glance counts */}
          <MetricStrip stats={stats} />

          {!isEmpty && <SystemStatusBanner />}

          {/* Quick actions */}
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              to="/dashboard/agents/new"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-5 py-2.5 text-sm font-medium text-brand-ink transition-colors hover:bg-brand-hover"
            >
              Create agent
              <span aria-hidden="true">+</span>
            </Link>
            <Link
              to="/dashboard/agents"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-line-strong bg-surface px-5 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-elevated"
            >
              View all agents
            </Link>
            <a
              href={ENDPOINTS.DOCS}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-line-strong bg-surface px-5 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-elevated"
            >
              API documentation
              <span aria-hidden="true">&rarr;</span>
            </a>
          </div>

          {/* Onboarding for empty state */}
          {isEmpty && <GettingStarted />}

          {/* Activity + Request Volume row */}
          {!isEmpty && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <RecentActivity agents={recentAgents} />
              <RequestVolumeChart />
            </div>
          )}

          {/* Agent Health + Quick Start row */}
          {!isEmpty && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <AgentHealthGrid agents={recentAgents} />
              <QuickStartBar />
            </div>
          )}
        </>
      )}
    </div>
  )
}
