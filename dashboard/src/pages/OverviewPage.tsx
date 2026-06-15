import { Link } from 'react-router-dom'
import { ENDPOINTS } from '../config/api'
import { useDashboardData } from '../hooks/useDashboardData'
import { StatsGrid } from '../components/StatsGrid'
import { RecentActivity } from '../components/RecentActivity'
import { GettingStarted } from '../components/GettingStarted'
import { SystemStatusBanner } from '../components/SystemStatusBanner'
import { RequestVolumeChart } from '../components/RequestVolumeChart'
import { AgentHealthGrid } from '../components/AgentHealthGrid'
import { QuickStartBar } from '../components/QuickStartBar'

export function OverviewPage() {
  const { stats, recentAgents, isLoading, error, isEmpty } = useDashboardData()

  return (
    <div className="space-y-8">
      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-8">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 animate-pulse rounded-xl bg-elevated" />
            ))}
          </div>
          <div className="h-64 animate-pulse rounded-xl bg-elevated" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-danger bg-danger-soft p-6">
          <h2 className="mb-1 font-semibold text-danger">
            {error.status === 401 ? 'Authentication Failed' : 'Unable to Load Dashboard'}
          </h2>
          <p className="text-sm text-danger">
            {error.status === 401
              ? 'Your session may have expired. Try signing out and back in.'
              : error.message}
          </p>
        </div>
      )}

      {/* Stats grid */}
      {!isLoading && !error && <StatsGrid stats={stats} />}

      {/* Quick actions */}
      {!isLoading && !error && (
        <div className="flex flex-col gap-3 sm:flex-row">
          <Link
            to="/dashboard/agents/new"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-6 py-3 font-semibold text-brand-ink transition-colors hover:bg-brand-hover"
          >
            Create Agent
            <span aria-hidden="true">+</span>
          </Link>
          <a
            href={ENDPOINTS.DOCS}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-line-strong bg-surface px-6 py-3 font-semibold text-muted transition-colors hover:bg-elevated"
          >
            API Documentation
            <span aria-hidden="true">&rarr;</span>
          </a>
          <a
            href={ENDPOINTS.GITHUB}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-line-strong bg-surface px-6 py-3 font-semibold text-muted transition-colors hover:bg-elevated"
          >
            GitHub
          </a>
        </div>
      )}

      {/* Onboarding for empty state */}
      {!isLoading && !error && isEmpty && <GettingStarted />}

      {/* System status banner */}
      {!isLoading && !error && !isEmpty && <SystemStatusBanner />}

      {/* Activity + Request Volume row */}
      {!isLoading && !error && !isEmpty && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RecentActivity agents={recentAgents} />
          <RequestVolumeChart />
        </div>
      )}

      {/* Agent Health + Quick Start row */}
      {!isLoading && !error && !isEmpty && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <AgentHealthGrid agents={recentAgents} />
          <QuickStartBar />
        </div>
      )}
    </div>
  )
}
