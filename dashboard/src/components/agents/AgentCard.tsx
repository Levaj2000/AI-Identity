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
      className="block rounded-xl border border-line bg-surface p-5 transition-colors hover:border-line-strong"
    >
      {/* Top row: name + status */}
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="truncate font-medium text-ink">{agent.name}</h3>
        <AgentStatusBadge status={agent.status} />
      </div>

      {/* Description */}
      {agent.description && (
        <p className="mb-3 truncate text-sm text-subtle">{agent.description}</p>
      )}

      {/* Capabilities */}
      {agent.capabilities.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {agent.capabilities.slice(0, 3).map((cap) => (
            <span
              key={cap}
              className="rounded-md bg-elevated px-2 py-0.5 font-[JetBrains_Mono,monospace] text-xs text-muted"
            >
              {cap}
            </span>
          ))}
          {agent.capabilities.length > 3 && (
            <span className="rounded-md bg-elevated px-2 py-0.5 text-xs text-subtle">
              +{agent.capabilities.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Footer: created date */}
      <p className="text-xs text-subtle">Created {relativeTime(agent.created_at)}</p>
    </Link>
  )
}
