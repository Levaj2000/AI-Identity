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
          className={`${base} text-emerald-500`}
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
          className={`${base} text-red-500`}
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
          className={`${base} text-amber-500`}
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
          className={`${base} text-gray-400`}
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
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#A6DAFF]/10 dark:bg-[#10131C]/80 dark:backdrop-blur-xl">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">
        Recent Activity
      </h2>

      <div className="space-y-3">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="flex items-center justify-between rounded-lg border border-l-2 border-transparent border-gray-200 bg-gray-50 px-4 py-3 transition-all duration-200 hover:border-l-[#A6DAFF] dark:border-[#1a1a1d] dark:border-l-transparent dark:bg-[#04070D]/50 dark:hover:border-l-[#A6DAFF] dark:hover:bg-[#A6DAFF]/5"
          >
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <StatusIcon status={agent.status} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-gray-900 dark:text-[#e4e4e7]">
                  {agent.name}
                </p>
                {agent.description && (
                  <p className="truncate text-sm text-gray-500 dark:text-[#71717a]">
                    {agent.description}
                  </p>
                )}
              </div>
            </div>

            <div className="ml-4 flex shrink-0 items-center gap-3">
              <AgentStatusBadge status={agent.status} />
              <span className="text-xs text-gray-400 dark:text-[#52525b]">
                {relativeTime(agent.updated_at)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
