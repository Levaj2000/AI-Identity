import type { Agent } from '../types/api'
import { relativeTime } from '../lib/time'

interface RecentActivityProps {
  agents: Agent[]
}

const statusStyles: Record<string, string> = {
  active: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
  suspended: 'border-amber-500/30 bg-amber-500/10 text-amber-400',
  revoked: 'border-red-500/30 bg-red-500/10 text-red-400',
}

export function RecentActivity({ agents }: RecentActivityProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-slate-100">
        Recent Activity
      </h2>

      <div className="space-y-3">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/50"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-gray-900 dark:text-slate-100">{agent.name}</p>
              {agent.description && (
                <p className="truncate text-sm text-gray-500 dark:text-slate-500">
                  {agent.description}
                </p>
              )}
            </div>

            <div className="ml-4 flex shrink-0 items-center gap-3">
              <span
                className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusStyles[agent.status] ?? ''}`}
              >
                {agent.status}
              </span>
              <span className="text-xs text-gray-400 dark:text-slate-600">
                {relativeTime(agent.updated_at)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
