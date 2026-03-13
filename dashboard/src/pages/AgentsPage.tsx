import { useAgentsList } from '../hooks/useAgentsList'
import { AgentFilters } from '../components/agents/AgentFilters'
import { AgentTable } from '../components/agents/AgentTable'
import { AgentCardGrid } from '../components/agents/AgentCardGrid'
import { AgentEmptyState } from '../components/agents/AgentEmptyState'
import { Pagination } from '../components/Pagination'

export function AgentsPage() {
  const {
    agents,
    total,
    isLoading,
    error,
    statusFilter,
    setStatusFilter,
    capabilityFilter,
    setCapabilityFilter,
    page,
    setPage,
    totalPages,
    pageSize,
  } = useAgentsList()

  const hasFilters = statusFilter !== undefined || capabilityFilter !== ''

  const clearFilters = () => {
    setStatusFilter(undefined)
    setCapabilityFilter('')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Agents</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
            Manage your AI agent identities and permissions.
          </p>
        </div>
        <button
          disabled
          className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg bg-indigo-600/50 px-4 py-2 text-sm font-semibold text-white/60"
          title="Coming soon"
        >
          New Agent
          <span className="rounded-full bg-indigo-500/30 px-2 py-0.5 text-xs">Soon</span>
        </button>
      </div>

      {/* Filters */}
      <AgentFilters
        status={statusFilter}
        onStatusChange={setStatusFilter}
        capability={capabilityFilter}
        onCapabilityChange={setCapabilityFilter}
      />

      {/* Loading skeleton */}
      {isLoading && (
        <>
          {/* Desktop skeleton: table rows */}
          <div className="hidden space-y-0 md:block">
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              {/* Header row */}
              <div className="border-b border-gray-200 px-6 py-3 dark:border-slate-800">
                <div className="h-3 w-48 animate-pulse rounded bg-gray-200 dark:bg-slate-800" />
              </div>
              {/* Body rows */}
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center gap-6 border-b border-gray-100 px-6 py-4 last:border-0 dark:border-slate-800/50"
                >
                  <div className="h-4 w-40 animate-pulse rounded bg-gray-200 dark:bg-slate-800" />
                  <div className="h-5 w-16 animate-pulse rounded-full bg-gray-200 dark:bg-slate-800" />
                  <div className="h-4 w-32 animate-pulse rounded bg-gray-200 dark:bg-slate-800" />
                  <div className="h-4 w-20 animate-pulse rounded bg-gray-200 dark:bg-slate-800" />
                </div>
              ))}
            </div>
          </div>
          {/* Mobile skeleton: cards */}
          <div className="space-y-3 md:hidden">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-28 animate-pulse rounded-xl bg-gray-200 dark:bg-slate-900"
              />
            ))}
          </div>
        </>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-6 dark:border-red-500/20 dark:bg-red-500/10">
          <h2 className="mb-1 font-semibold text-red-600 dark:text-red-400">
            {error.status === 401 ? 'Authentication Failed' : 'Unable to Load Agents'}
          </h2>
          <p className="text-sm text-red-500 dark:text-red-400/80">
            {error.status === 401
              ? 'Check your API key configuration. Set VITE_API_KEY in your .env file.'
              : error.message}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && agents.length === 0 && (
        <AgentEmptyState hasFilters={hasFilters} onClearFilters={clearFilters} />
      )}

      {/* Agent list */}
      {!isLoading && !error && agents.length > 0 && (
        <>
          {/* Desktop table */}
          <div className="hidden md:block">
            <AgentTable agents={agents} />
          </div>
          {/* Mobile cards */}
          <div className="md:hidden">
            <AgentCardGrid agents={agents} />
          </div>
        </>
      )}

      {/* Pagination */}
      {!isLoading && !error && totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          pageSize={pageSize}
          onPageChange={setPage}
        />
      )}
    </div>
  )
}
