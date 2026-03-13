import { useNavigate } from 'react-router-dom'
import { AgentStatusBadge } from '../AgentStatusBadge'
import { relativeTime } from '../../lib/time'
import type { Agent } from '../../types/api'

interface AgentTableProps {
  agents: Agent[]
}

export function AgentTable({ agents }: AgentTableProps) {
  const navigate = useNavigate()

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200 dark:border-slate-800">
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-slate-400">
              Name
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-slate-400">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-slate-400">
              Capabilities
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-slate-400">
              Created
            </th>
            <th className="w-10 px-3 py-3">
              <span className="sr-only">View</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-slate-800/50">
          {agents.map((agent) => (
            <tr
              key={agent.id}
              onClick={() => navigate(`/agents/${agent.id}`)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') navigate(`/agents/${agent.id}`)
              }}
              role="link"
              tabIndex={0}
              className="cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-slate-800/50"
            >
              {/* Name + description */}
              <td className="px-6 py-4">
                <div className="max-w-xs">
                  <p className="truncate font-medium text-gray-900 dark:text-slate-100">
                    {agent.name}
                  </p>
                  {agent.description && (
                    <p className="truncate text-sm text-gray-500 dark:text-slate-400">
                      {agent.description}
                    </p>
                  )}
                </div>
              </td>

              {/* Status badge */}
              <td className="px-6 py-4">
                <AgentStatusBadge status={agent.status} />
              </td>

              {/* Capabilities tags */}
              <td className="px-6 py-4">
                <div className="flex flex-wrap gap-1.5">
                  {agent.capabilities.slice(0, 3).map((cap) => (
                    <span
                      key={cap}
                      className="rounded-md bg-gray-100 px-2 py-0.5 font-[JetBrains_Mono,monospace] text-xs text-gray-600 dark:bg-slate-800 dark:text-slate-400"
                    >
                      {cap}
                    </span>
                  ))}
                  {agent.capabilities.length > 3 && (
                    <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-slate-800 dark:text-slate-500">
                      +{agent.capabilities.length - 3}
                    </span>
                  )}
                  {agent.capabilities.length === 0 && (
                    <span className="text-xs text-gray-400 dark:text-slate-600">&mdash;</span>
                  )}
                </div>
              </td>

              {/* Created date */}
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500 dark:text-slate-400">
                {relativeTime(agent.created_at)}
              </td>

              {/* Chevron */}
              <td className="px-3 py-4 text-gray-400 dark:text-slate-600">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-5 w-5"
                >
                  <path
                    fillRule="evenodd"
                    d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                    clipRule="evenodd"
                  />
                </svg>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
