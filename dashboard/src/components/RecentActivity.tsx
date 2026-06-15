import type { Agent } from '../types/api'
import { relativeTime } from '../lib/time'
import { AgentStatusBadge } from './AgentStatusBadge'

interface RecentActivityProps {
  agents: Agent[]
}

function StatusIcon({ status }: { status: string }) {
  const base = 'h-4 w-4 shrink-0'
  switch (status) {
    case 'active':
      return (
        <svg
          className={`${base} text-success`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      )
    case 'revoked':
      return (
        <svg
          className={`${base} text-danger`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      )
    case 'suspended':
      return (
        <svg
          className={`${base} text-warning`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      )
    default:
      return (
        <svg
          className={`${base} text-faint`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      )
  }
}

export function RecentActivity({ agents }: RecentActivityProps) {
  return (
    <div className="rounded-xl border border-line bg-surface p-6">
      <h2 className="mb-4 text-lg font-semibold text-ink">Recent Activity</h2>

      <div className="space-y-3">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="flex items-center justify-between rounded-lg border border-l-2 border-transparent border-line bg-inset px-4 py-3 transition-all duration-200 hover:border-l-brand hover:bg-brand-soft"
          >
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <StatusIcon status={agent.status} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-ink">{agent.name}</p>
                {agent.description && (
                  <p className="truncate text-sm text-subtle">{agent.description}</p>
                )}
              </div>
            </div>

            <div className="ml-4 flex shrink-0 items-center gap-3">
              <AgentStatusBadge status={agent.status} />
              <span className="text-xs text-faint">{relativeTime(agent.updated_at)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
