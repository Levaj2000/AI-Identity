import type { AgentKey } from '../../types/api'
import { KeyStatusBadge } from '../KeyStatusBadge'
import { relativeTime } from '../../lib/time'
import { formatCountdown } from '../../lib/time'

interface KeyTableProps {
  keys: AgentKey[]
  isAgentRevoked: boolean
  onRevoke: (keyId: number) => void
}

/**
 * Key list table with visual hierarchy by status.
 *
 * - Active rows: normal styling, prominent
 * - Rotated rows: amber left-border accent, countdown in Expires column
 * - Revoked rows: muted text, strikethrough on prefix
 */
export function KeyTable({ keys, isAgentRevoked, onRevoke }: KeyTableProps) {
  if (keys.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-8 text-center dark:border-[#2a2a2d] dark:bg-[#111113]/50">
        <p className="text-sm text-gray-500 dark:text-[#71717a]">No keys match this filter.</p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-[#1a1a1d]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 dark:border-[#2a2a2d] dark:bg-[#1a1a1d]/50">
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-[#a1a1aa]">
              Key Prefix
            </th>
            <th className="hidden px-4 py-3 text-left font-medium text-gray-600 dark:text-[#a1a1aa] sm:table-cell">
              Type
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-[#a1a1aa]">
              Status
            </th>
            <th className="hidden px-4 py-3 text-left font-medium text-gray-600 dark:text-[#a1a1aa] md:table-cell">
              Created
            </th>
            <th className="hidden px-4 py-3 text-left font-medium text-gray-600 dark:text-[#a1a1aa] sm:table-cell">
              Expires
            </th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-[#a1a1aa]">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {keys.map((key) => (
            <KeyRow
              key={key.id}
              agentKey={key}
              isAgentRevoked={isAgentRevoked}
              onRevoke={onRevoke}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Row ──────────────────────────────────────────────────────────

interface KeyRowProps {
  agentKey: AgentKey
  isAgentRevoked: boolean
  onRevoke: (keyId: number) => void
}

function KeyRow({ agentKey, isAgentRevoked, onRevoke }: KeyRowProps) {
  const isRevoked = agentKey.status === 'revoked'
  const isRotated = agentKey.status === 'rotated'

  // Row styling by status
  const rowClass = isRevoked
    ? 'opacity-60'
    : isRotated
      ? 'border-l-2 border-l-amber-400 dark:border-l-amber-500'
      : ''

  // Whether the revoke button should be shown/enabled
  const canRevoke = !isRevoked && !isAgentRevoked

  return (
    <tr className={`border-b border-gray-100 last:border-b-0 dark:border-[#1a1a1d] ${rowClass}`}>
      {/* Key Prefix */}
      <td className="px-4 py-3">
        <code
          className={`font-[JetBrains_Mono,monospace] text-xs text-gray-900 dark:text-[#e4e4e7] ${
            isRevoked ? 'line-through' : ''
          }`}
        >
          {agentKey.key_prefix}...
        </code>
      </td>

      {/* Type */}
      <td className="hidden px-4 py-3 sm:table-cell">
        <span className="text-xs capitalize text-gray-600 dark:text-[#a1a1aa]">
          {agentKey.key_type}
        </span>
      </td>

      {/* Status */}
      <td className="px-4 py-3">
        <KeyStatusBadge status={agentKey.status} />
      </td>

      {/* Created */}
      <td className="hidden px-4 py-3 text-gray-600 dark:text-[#a1a1aa] md:table-cell">
        {relativeTime(agentKey.created_at)}
      </td>

      {/* Expires */}
      <td className="hidden px-4 py-3 sm:table-cell">
        {isRotated && agentKey.expires_at ? (
          <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
            {formatCountdown(agentKey.expires_at)}
          </span>
        ) : (
          <span className="text-gray-400 dark:text-[#52525b]">&mdash;</span>
        )}
      </td>

      {/* Actions */}
      <td className="px-4 py-3 text-right">
        {canRevoke ? (
          <button
            type="button"
            onClick={() => onRevoke(agentKey.id)}
            className="rounded-md border border-red-300 px-2.5 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 dark:border-red-500/30 dark:text-red-400 dark:hover:bg-red-500/10"
          >
            Revoke
          </button>
        ) : isRevoked ? (
          <span className="text-xs text-gray-400 dark:text-[#52525b]">Revoked</span>
        ) : (
          <span className="text-xs text-gray-400 dark:text-[#52525b]">&mdash;</span>
        )}
      </td>
    </tr>
  )
}
