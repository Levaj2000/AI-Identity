import { CheckCircle, XCircle, PauseCircle } from 'lucide-react'
import type { Agent } from '../types/api'
import { relativeTime } from '../lib/time'
import { AgentStatusBadge } from './AgentStatusBadge'

interface RecentActivityProps {
  agents: Agent[]
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'active':
      return <CheckCircle className="h-4 w-4 shrink-0 text-emerald-500" />
    case 'revoked':
      return <XCircle className="h-4 w-4 shrink-0 text-red-500" />
    case 'suspended':
      return <PauseCircle className="h-4 w-4 shrink-0 text-amber-500" />
    default:
      return <CheckCircle className="h-4 w-4 shrink-0 text-gray-400" />
  }
}

export function RecentActivity({ agents }: RecentActivityProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#00FFC2]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">
        Recent Activity
      </h2>

      <div className="space-y-3">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="flex items-center justify-between rounded-lg border border-l-2 border-transparent border-gray-200 bg-gray-50 px-4 py-3 transition-all duration-200 hover:border-l-[#00FFC2] dark:border-[#1a1a1d] dark:border-l-transparent dark:bg-[#0A0A0B]/50 dark:hover:border-l-[#00FFC2] dark:hover:bg-[#00FFC2]/5"
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
