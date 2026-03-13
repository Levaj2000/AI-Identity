import type { KeyStatus } from '../types/api'

const statusStyles: Record<KeyStatus, string> = {
  active:
    'border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
  rotated:
    'border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
  revoked: 'border-red-500/30 bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400',
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
