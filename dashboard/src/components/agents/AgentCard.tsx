import { Link } from 'react-router-dom'
import { AgentStatusBadge } from '../AgentStatusBadge'
import { relativeTime } from '../../lib/time'
import type { Agent } from '../../types/api'

interface AgentCardProps {
  agent: Agent
}

export function AgentCard({ agent }: AgentCardProps) {
  return (
    <Link
      to={`/dashboard/agents/${agent.id}`}
      className="block rounded-xl border border-gray-200 bg-white p-5 transition-colors hover:border-gray-300 dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl dark:hover:border-[#F59E0B]/25"
    >
      {/* Top row: name + status */}
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="truncate font-medium text-gray-900 dark:text-[#e4e4e7]">{agent.name}</h3>
        <AgentStatusBadge status={agent.status} />
      </div>

      {/* Description */}
      {agent.description && (
        <p className="mb-3 truncate text-sm text-gray-500 dark:text-[#a1a1aa]">
          {agent.description}
        </p>
      )}

      {/* Capabilities */}
      {agent.capabilities.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
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
        </div>
      )}

      {/* Footer: created date */}
      <p className="text-xs text-gray-400 dark:text-[#71717a]">
        Created {relativeTime(agent.created_at)}
      </p>
    </Link>
  )
}
