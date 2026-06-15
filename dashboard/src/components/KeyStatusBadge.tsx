import type { KeyStatus } from '../types/api'

const statusStyles: Record<KeyStatus, string> = {
  active: 'border-success bg-success-soft text-success',
  rotated: 'border-warning bg-warning-soft text-warning',
  revoked: 'border-danger bg-danger-soft text-danger',
}

interface KeyStatusBadgeProps {
  status: KeyStatus
}

export function KeyStatusBadge({ status }: KeyStatusBadgeProps) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${statusStyles[status]}`}
    >
      {status}
    </span>
  )
}
