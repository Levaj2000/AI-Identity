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
      <div className="rounded-xl border border-dashed border-line-strong bg-inset p-8 text-center">
        <p className="text-sm text-subtle">No keys match this filter.</p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line bg-elevated">
            <th className="px-4 py-3 text-left font-medium text-muted">Key Prefix</th>
            <th className="hidden px-4 py-3 text-left font-medium text-muted sm:table-cell">
              Type
            </th>
            <th className="px-4 py-3 text-left font-medium text-muted">Status</th>
            <th className="hidden px-4 py-3 text-left font-medium text-muted md:table-cell">
              Created
            </th>
            <th className="hidden px-4 py-3 text-left font-medium text-muted sm:table-cell">
              Expires
            </th>
            <th className="px-4 py-3 text-right font-medium text-muted">Actions</th>
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
  const rowClass = isRevoked ? 'opacity-60' : isRotated ? 'border-l-2 border-l-warning' : ''

  // Whether the revoke button should be shown/enabled
  const canRevoke = !isRevoked && !isAgentRevoked

  return (
    <tr className={`border-b border-line last:border-b-0 ${rowClass}`}>
      {/* Key Prefix */}
      <td className="px-4 py-3">
        <code
          className={`font-[JetBrains_Mono,monospace] text-xs text-ink ${
            isRevoked ? 'line-through' : ''
          }`}
        >
          {agentKey.key_prefix}...
        </code>
      </td>

      {/* Type */}
      <td className="hidden px-4 py-3 sm:table-cell">
        <span className="text-xs capitalize text-muted">{agentKey.key_type}</span>
      </td>

      {/* Status */}
      <td className="px-4 py-3">
        <KeyStatusBadge status={agentKey.status} />
      </td>

      {/* Created */}
      <td className="hidden px-4 py-3 text-muted md:table-cell">
        {relativeTime(agentKey.created_at)}
      </td>

      {/* Expires */}
      <td className="hidden px-4 py-3 sm:table-cell">
        {isRotated && agentKey.expires_at ? (
          <span className="text-xs font-medium text-warning">
            {formatCountdown(agentKey.expires_at)}
          </span>
        ) : (
          <span className="text-faint">&mdash;</span>
        )}
      </td>

      {/* Actions */}
      <td className="px-4 py-3 text-right">
        {canRevoke ? (
          <button
            type="button"
            onClick={() => onRevoke(agentKey.id)}
            className="rounded-md border border-danger px-2.5 py-1 text-xs font-medium text-danger transition-colors hover:bg-danger-soft"
          >
            Revoke
          </button>
        ) : isRevoked ? (
          <span className="text-xs text-faint">Revoked</span>
        ) : (
          <span className="text-xs text-faint">&mdash;</span>
        )}
      </td>
    </tr>
  )
}
