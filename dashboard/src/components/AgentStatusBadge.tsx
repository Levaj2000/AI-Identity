import type { AgentStatus } from '../types/api'

const statusStyles: Record<AgentStatus, string> = {
  active: 'border-success bg-success-soft text-success',
  suspended: 'border-warning bg-warning-soft text-warning',
  revoked: 'border-danger bg-danger-soft text-danger',
}

interface AgentStatusBadgeProps {
  status: AgentStatus
}

export function AgentStatusBadge({ status }: AgentStatusBadgeProps) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${statusStyles[status]}`}
    >
      {status}
    </span>
  )
}
