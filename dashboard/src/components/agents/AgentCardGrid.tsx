import { AgentCard } from './AgentCard'
import type { Agent } from '../../types/api'

interface AgentCardGridProps {
  agents: Agent[]
}

export function AgentCardGrid({ agents }: AgentCardGridProps) {
  return (
    <div className="space-y-3">
      {agents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  )
}
