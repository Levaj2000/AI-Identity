import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AgentStatusBadge } from '../AgentStatusBadge'
import { relativeTime } from '../../lib/time'
import { purgeSingleAgent } from '../../services/api/admin'
import type { Agent } from '../../types/api'

interface AgentTableProps {
  agents: Agent[]
  isAdmin?: boolean
  onAgentDeleted?: () => void
}

export function AgentTable({ agents, isAdmin, onAgentDeleted }: AgentTableProps) {
  const navigate = useNavigate()
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const handleDelete = async (e: React.MouseEvent, agentId: string) => {
    e.stopPropagation()
    if (confirmId === agentId) {
      setDeleting(agentId)
      try {
        await purgeSingleAgent(agentId)
        onAgentDeleted?.()
      } catch {
        // Error silently handled
      } finally {
        setDeleting(null)
        setConfirmId(null)
      }
    } else {
      setConfirmId(agentId)
    }
  }

  const cancelConfirm = (e: React.MouseEvent) => {
    e.stopPropagation()
    setConfirmId(null)
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-[#A6DAFF]/10 dark:bg-[#10131C]/80 dark:backdrop-blur-xl">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200 dark:border-[#1a1a1d]">
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
              Name
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
              Capabilities
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
              Created
            </th>
            <th className="w-10 px-3 py-3">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-[#1a1a1d]/50">
          {agents.map((agent) => (
            <tr
              key={agent.id}
              onClick={() => navigate(`/dashboard/agents/${agent.id}`)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') navigate(`/dashboard/agents/${agent.id}`)
              }}
              role="link"
              tabIndex={0}
              className="cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-[#1a1a1d]/50"
            >
              {/* Name + description */}
              <td className="px-6 py-4">
                <div className="max-w-xs">
                  <p className="truncate font-medium text-gray-900 dark:text-[#e4e4e7]">
                    {agent.name}
                  </p>
                  {agent.description && (
                    <p className="truncate text-sm text-gray-500 dark:text-[#a1a1aa]">
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
                      className="rounded-md bg-gray-100 px-2 py-0.5 font-[JetBrains_Mono,monospace] text-xs text-gray-600 dark:bg-[#1a1a1d] dark:text-[#a1a1aa]"
                    >
                      {cap}
                    </span>
                  ))}
                  {agent.capabilities.length > 3 && (
                    <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-[#1a1a1d] dark:text-[#71717a]">
                      +{agent.capabilities.length - 3}
                    </span>
                  )}
                  {agent.capabilities.length === 0 && (
                    <span className="text-xs text-gray-400 dark:text-[#52525b]">&mdash;</span>
                  )}
                </div>
              </td>

              {/* Created date */}
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500 dark:text-[#a1a1aa]">
                {relativeTime(agent.created_at)}
              </td>

              {/* Actions: delete (admin) or chevron */}
              <td className="px-3 py-4">
                {isAdmin ? (
                  <div className="flex items-center gap-1">
                    {confirmId === agent.id ? (
                      <>
                        <button
                          onClick={(e) => handleDelete(e, agent.id)}
                          disabled={deleting === agent.id}
                          className="rounded px-2 py-1 text-xs font-medium text-red-500 transition-colors hover:bg-red-500/10 disabled:opacity-50"
                          title="Confirm delete"
                        >
                          {deleting === agent.id ? '...' : 'Delete'}
                        </button>
                        <button
                          onClick={cancelConfirm}
                          className="rounded px-2 py-1 text-xs text-gray-400 transition-colors hover:bg-gray-500/10"
                          title="Cancel"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={(e) => handleDelete(e, agent.id)}
                        className="rounded p-1 text-gray-400 transition-colors hover:bg-red-500/10 hover:text-red-500 dark:text-[#52525b] dark:hover:text-red-400"
                        title="Delete permanently"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                          className="h-4 w-4"
                        >
                          <path
                            fillRule="evenodd"
                            d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </button>
                    )}
                  </div>
                ) : (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-5 w-5 text-gray-400 dark:text-[#52525b]"
                  >
                    <path
                      fillRule="evenodd"
                      d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
