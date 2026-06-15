import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAgentsList } from '../hooks/useAgentsList'
import { useAuth } from '../hooks/useAuth'
import { purgeRevokedAgents } from '../services/api/admin'
import { AgentFilters } from '../components/agents/AgentFilters'
import { AgentTable } from '../components/agents/AgentTable'
import { AgentCardGrid } from '../components/agents/AgentCardGrid'
import { AgentEmptyState } from '../components/agents/AgentEmptyState'
import { Pagination } from '../components/Pagination'

export function AgentsPage() {
  const { user } = useAuth()
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
    refetch,
  } = useAgentsList()

  const [purging, setPurging] = useState(false)
  const [showPurgeConfirm, setShowPurgeConfirm] = useState(false)
  const [purgeResult, setPurgeResult] = useState<{ count: number; names: string[] } | null>(null)

  const isAdmin = user?.role === 'admin'
  const showPurgeButton = isAdmin && statusFilter === 'revoked' && agents.length > 0

  const handlePurge = async () => {
    setPurging(true)
    setShowPurgeConfirm(false)
    try {
      const result = await purgeRevokedAgents(0)
      setPurgeResult({ count: result.purged_count, names: result.agent_names })
      refetch()
    } catch {
      // Error handled by UI
    } finally {
      setPurging(false)
    }
  }

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
          <h1 className="text-2xl font-bold text-ink">Agents</h1>
          <p className="mt-1 text-sm text-muted">
            Manage your AI agent identities and permissions.
          </p>
        </div>
        <Link
          to="/dashboard/agents/new"
          className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brand-ink transition-colors hover:bg-brand-hover"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
          </svg>
          New Agent
        </Link>
      </div>

      {/* Filters */}
      <AgentFilters
        status={statusFilter}
        onStatusChange={setStatusFilter}
        capability={capabilityFilter}
        onCapabilityChange={setCapabilityFilter}
      />

      {/* Purge revoked agents (admin only) */}
      {showPurgeButton && (
        <div className="flex items-center justify-between rounded-xl border border-danger bg-danger-soft px-4 py-3">
          <p className="text-sm text-danger">
            {total} revoked agent{total !== 1 ? 's' : ''} found.
          </p>
          <button
            onClick={() => setShowPurgeConfirm(true)}
            disabled={purging}
            className="rounded-lg bg-danger px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-danger disabled:opacity-50"
          >
            {purging ? 'Purging...' : 'Purge All'}
          </button>
        </div>
      )}

      {/* Purge confirmation modal */}
      {showPurgeConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 w-full max-w-md rounded-xl border border-line bg-surface p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-ink">Purge Revoked Agents</h3>
            <p className="mt-2 text-sm text-muted">
              This will permanently delete {total} revoked agent{total !== 1 ? 's' : ''} and all
              associated keys, policies, and credentials. Audit logs will be preserved.
            </p>
            <p className="mt-2 text-sm font-medium text-danger">This action cannot be undone.</p>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => setShowPurgeConfirm(false)}
                className="rounded-lg border border-line-strong px-4 py-2 text-sm font-medium text-muted transition-colors hover:bg-elevated"
              >
                Cancel
              </button>
              <button
                onClick={handlePurge}
                className="rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-danger"
              >
                Purge {total} Agent{total !== 1 ? 's' : ''}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Purge result toast */}
      {purgeResult && (
        <div className="rounded-xl border border-success bg-success-soft px-4 py-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-success">
              Purged {purgeResult.count} agent{purgeResult.count !== 1 ? 's' : ''}.
            </p>
            <button
              onClick={() => setPurgeResult(null)}
              className="text-success hover:text-success"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <>
          {/* Desktop skeleton: table rows */}
          <div className="hidden space-y-0 md:block">
            <div className="overflow-hidden rounded-xl border border-line bg-surface">
              {/* Header row */}
              <div className="border-b border-line px-6 py-3">
                <div className="h-3 w-48 animate-pulse rounded bg-elevated" />
              </div>
              {/* Body rows */}
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center gap-6 border-b border-line px-6 py-4 last:border-0"
                >
                  <div className="h-4 w-40 animate-pulse rounded bg-elevated" />
                  <div className="h-5 w-16 animate-pulse rounded-full bg-elevated" />
                  <div className="h-4 w-32 animate-pulse rounded bg-elevated" />
                  <div className="h-4 w-20 animate-pulse rounded bg-elevated" />
                </div>
              ))}
            </div>
          </div>
          {/* Mobile skeleton: cards */}
          <div className="space-y-3 md:hidden">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 animate-pulse rounded-xl bg-elevated" />
            ))}
          </div>
        </>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-danger bg-danger-soft p-6">
          <h2 className="mb-1 font-semibold text-danger">
            {error.status === 401 ? 'Authentication Failed' : 'Unable to Load Agents'}
          </h2>
          <p className="text-sm text-danger">
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
            <AgentTable agents={agents} isAdmin={isAdmin} onAgentDeleted={refetch} />
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
