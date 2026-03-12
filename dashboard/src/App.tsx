import { ENDPOINTS } from './config/api'
import { useHealthCheck } from './hooks/useHealthCheck'
import { useDashboardData } from './hooks/useDashboardData'
import { HealthIndicator } from './components/HealthIndicator'
import { StatsGrid } from './components/StatsGrid'
import { RecentActivity } from './components/RecentActivity'
import { GettingStarted } from './components/GettingStarted'

function App() {
  const health = useHealthCheck()
  const { stats, recentAgents, isLoading, error, isEmpty } = useDashboardData()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-[Inter,system-ui,sans-serif]">
      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              <span className="text-indigo-500">AI</span> Identity
            </h1>
            <p className="text-sm text-slate-500">Identity for AI agents</p>
          </div>
          <HealthIndicator isHealthy={health.isHealthy} version={health.version} />
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
        {/* Loading skeleton */}
        {isLoading && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-28 animate-pulse rounded-xl bg-slate-900" />
              ))}
            </div>
            <div className="h-64 animate-pulse rounded-xl bg-slate-900" />
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6">
            <h2 className="mb-1 font-semibold text-red-400">
              {error.status === 401 ? 'Authentication Failed' : 'Unable to Load Dashboard'}
            </h2>
            <p className="text-sm text-red-400/80">
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
              className="inline-flex cursor-not-allowed items-center justify-center gap-2 rounded-lg bg-indigo-600/50 px-6 py-3 font-semibold text-white/60"
              title="Coming soon"
            >
              Create Agent
              <span className="rounded-full bg-indigo-500/30 px-2 py-0.5 text-xs">Soon</span>
            </button>
            <a
              href={ENDPOINTS.DOCS}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-6 py-3 font-semibold text-slate-200 transition-colors hover:bg-slate-700"
            >
              API Documentation
              <span aria-hidden="true">&rarr;</span>
            </a>
            <a
              href={ENDPOINTS.GITHUB}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-6 py-3 font-semibold text-slate-200 transition-colors hover:bg-slate-700"
            >
              GitHub
            </a>
          </div>
        )}

        {/* Content: onboarding or activity */}
        {!isLoading && !error && isEmpty && <GettingStarted />}
        {!isLoading && !error && !isEmpty && <RecentActivity agents={recentAgents} />}
      </main>

      {/* Footer */}
      <footer className="py-8 text-center text-sm text-slate-600">
        <p>&copy; {new Date().getFullYear()} AI Identity. All rights reserved.</p>
      </footer>
    </div>
  )
}

export default App
