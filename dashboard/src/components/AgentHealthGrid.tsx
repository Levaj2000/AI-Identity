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
    active: 'bg-success',
    suspended: 'bg-warning',
    revoked: 'bg-danger',
  }
  const color = colorMap[status] || 'bg-subtle'
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
      return 'text-success'
    case 'suspended':
      return 'text-warning'
    case 'revoked':
      return 'text-danger'
    default:
      return 'text-faint'
  }
}

export function AgentHealthGrid({ agents }: AgentHealthGridProps) {
  return (
    <div className="rounded-xl border border-line bg-surface p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-ink">Agent Health</h2>
        <p className="text-sm text-subtle">
          {agents.length} agent{agents.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="rounded-lg border border-line bg-inset p-4 transition-all duration-200 hover:border-line-strong hover:bg-brand-soft"
          >
            <div className="flex items-center gap-3">
              <StatusDot status={agent.status} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <p className="truncate font-medium text-ink">{agent.name}</p>
                  <span
                    className={`ml-2 shrink-0 text-xs font-medium ${statusColor(agent.status)}`}
                  >
                    {statusLabel(agent.status)}
                  </span>
                </div>
                {agent.description && (
                  <p className="mt-0.5 truncate text-sm text-subtle">{agent.description}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
