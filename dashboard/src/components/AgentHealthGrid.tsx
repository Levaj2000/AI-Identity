interface AgentHealthItem {
  id: string
  name: string
  status: string
  description?: string | null
}

interface AgentHealthGridProps {
  agents: AgentHealthItem[]
}

function StatusDot({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    active: 'bg-emerald-500',
    suspended: 'bg-amber-500',
    revoked: 'bg-red-500',
  }
  const color = colorMap[status] || 'bg-gray-400'
  const isActive = status === 'active'

  return (
    <span className="relative flex h-3 w-3 shrink-0">
      {isActive && (
        <span
          className={`absolute inline-flex h-full w-full animate-ping rounded-full ${color} opacity-75`}
          style={{ animationDuration: '2s' }}
        />
      )}
      <span className={`relative inline-flex h-3 w-3 rounded-full ${color}`} />
    </span>
  )
}

function statusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function statusColor(status: string): string {
  switch (status) {
    case 'active':
      return 'text-emerald-500'
    case 'suspended':
      return 'text-amber-500'
    case 'revoked':
      return 'text-red-500'
    default:
      return 'text-gray-400'
  }
}

export function AgentHealthGrid({ agents }: AgentHealthGridProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#A6DAFF]/10 dark:bg-[#10131C]/80 dark:backdrop-blur-xl">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">Agent Health</h2>
        <p className="text-sm text-gray-500 dark:text-[#71717a]">
          {agents.length} agent{agents.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="rounded-lg border border-gray-200 bg-gray-50 p-4 transition-all duration-200 hover:border-[#A6DAFF]/30 hover:bg-gray-100 dark:border-[#1a1a1d] dark:bg-[#04070D]/50 dark:hover:border-[#A6DAFF]/30 dark:hover:bg-[#A6DAFF]/5"
          >
            <div className="flex items-center gap-3">
              <StatusDot status={agent.status} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <p className="truncate font-medium text-gray-900 dark:text-white">{agent.name}</p>
                  <span
                    className={`ml-2 shrink-0 text-xs font-medium ${statusColor(agent.status)}`}
                  >
                    {statusLabel(agent.status)}
                  </span>
                </div>
                {agent.description && (
                  <p className="mt-0.5 truncate text-sm text-gray-500 dark:text-[#71717a]">
                    {agent.description}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
