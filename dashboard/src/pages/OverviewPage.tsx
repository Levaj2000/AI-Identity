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
              <div
                key={i}
                className="h-28 animate-pulse rounded-xl bg-gray-200 dark:bg-[#111113]"
              />
            ))}
          </div>
          <div className="h-64 animate-pulse rounded-xl bg-gray-200 dark:bg-[#111113]" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-6 dark:border-red-500/20 dark:bg-red-500/10">
          <h2 className="mb-1 font-semibold text-red-600 dark:text-red-400">
            {error.status === 401 ? 'Authentication Failed' : 'Unable to Load Dashboard'}
          </h2>
          <p className="text-sm text-red-500 dark:text-red-400/80">
            {error.status === 401
              ? 'Check your API key configuration. Set VITE_API_KEY in your .env file.'
              : error.message}
          </p>
        </div>
      )}

      {/* Stats grid */}
      {!isLoading && !error && <StatsGrid stats={stats} />}

      {/* Quick actions */}
      {!isLoading && !error && (
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            disabled
            className="inline-flex cursor-not-allowed items-center justify-center gap-2 rounded-lg bg-[#F59E0B]/50 px-6 py-3 font-semibold text-[#0A0A0B]/60"
            title="Coming soon"
          >
            Create Agent
            <span className="rounded-full bg-[#F59E0B]/30 px-2 py-0.5 text-xs">Soon</span>
          </button>
          <a
            href={ENDPOINTS.DOCS}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 font-semibold text-gray-700 transition-colors hover:bg-gray-50 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#e4e4e7] dark:hover:bg-[#2a2a2d]"
          >
            API Documentation
            <span aria-hidden="true">&rarr;</span>
          </a>
          <a
            href={ENDPOINTS.GITHUB}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 font-semibold text-gray-700 transition-colors hover:bg-gray-50 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#e4e4e7] dark:hover:bg-[#2a2a2d]"
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
