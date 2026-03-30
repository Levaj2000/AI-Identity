import { useEffect, useState, useCallback } from 'react'
import {
  getApprovals,
  resolveApproval,
  type Approval,
  type ApprovalList,
} from '../services/api/approvals'
import { isApiError } from '../services/api/client'

type StatusFilter = '' | 'pending' | 'approved' | 'rejected' | 'expired'

const STATUS_TABS: { label: string; value: StatusFilter }[] = [
  { label: 'All', value: '' },
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Rejected', value: 'rejected' },
  { label: 'Expired', value: 'expired' },
]

export function ApprovalsPage() {
  const [data, setData] = useState<ApprovalList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending')
  const [page, setPage] = useState(0)
  const [resolving, setResolving] = useState<string | null>(null)
  const [selectedApproval, setSelectedApproval] = useState<Approval | null>(null)
  const pageSize = 20

  const loadData = useCallback(
    async (status?: StatusFilter, currentPage?: number) => {
      try {
        setLoading(true)
        setError(null)
        const params: { limit: number; offset: number; status?: string } = {
          limit: pageSize,
          offset: (currentPage ?? page) * pageSize,
        }
        const s = status ?? statusFilter
        if (s) params.status = s
        const res = await getApprovals(params)
        setData(res)
      } catch (err) {
        if (isApiError(err) && err.status === 403) {
          setError('Access denied')
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load approvals')
        }
      } finally {
        setLoading(false)
      }
    },
    [page, statusFilter, pageSize],
  )

  // Initial load + auto-refresh every 10s
  useEffect(() => {
    loadData()
    const interval = setInterval(() => loadData(), 10000)
    return () => clearInterval(interval)
  }, [loadData])

  const handleStatusFilter = (status: StatusFilter) => {
    setStatusFilter(status)
    setPage(0)
    loadData(status, 0)
  }

  const handleResolve = async (id: string, action: 'approve' | 'reject') => {
    const label = action === 'approve' ? 'APPROVE' : 'REJECT'
    if (!confirm(`${label} this request?`)) return

    setResolving(id)
    try {
      await resolveApproval(id, action)
      await loadData()
      setSelectedApproval(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : `Failed to ${action}`)
    } finally {
      setResolving(null)
    }
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    loadData(statusFilter, newPage)
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-red-400">
          <h3 className="font-semibold mb-1">Error</h3>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Approvals</h1>
        <p className="text-gray-400 mt-1">Human-in-the-loop review for sensitive agent actions</p>
      </div>

      {/* Status Tabs */}
      <div className="flex gap-1 bg-[#10131C] border border-[#1a1a1d] rounded-xl p-1">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => handleStatusFilter(tab.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === tab.value
                ? 'bg-[#A6DAFF]/10 text-[#A6DAFF]'
                : 'text-gray-400 hover:text-white hover:bg-[#1a1a1d]'
            }`}
          >
            {tab.label}
            {tab.value === 'pending' && data && statusFilter !== 'pending' && <PendingDot />}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-[#10131C] border border-[#1a1a1d] rounded-xl overflow-hidden">
        {loading && !data ? (
          <div className="px-5 py-12 text-center text-gray-500">Loading approvals...</div>
        ) : data?.items.length === 0 ? (
          <div className="px-5 py-12 text-center text-gray-500">
            {statusFilter ? `No ${statusFilter} approvals` : 'No approval requests yet'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-[#1a1a1d]">
                  <th className="px-5 py-3 font-medium">Timestamp</th>
                  <th className="px-5 py-3 font-medium">Agent</th>
                  <th className="px-5 py-3 font-medium">Endpoint</th>
                  <th className="px-5 py-3 font-medium">Method</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Expires</th>
                  <th className="px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-[#1a1a1d]/50 hover:bg-[#1a1a1d]/30 transition-colors cursor-pointer"
                    onClick={() => setSelectedApproval(item)}
                  >
                    <td className="px-5 py-3 text-gray-400 whitespace-nowrap">
                      {formatDateTime(item.created_at)}
                    </td>
                    <td className="px-5 py-3 text-gray-300">
                      {item.agent_name || (
                        <span className="text-gray-500 font-mono text-xs">
                          {item.agent_id.slice(0, 8)}...
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <span className="text-gray-300 font-mono text-xs">{item.endpoint}</span>
                    </td>
                    <td className="px-5 py-3">
                      <MethodBadge method={item.method} />
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-5 py-3 text-gray-400 whitespace-nowrap text-xs">
                      {item.status === 'pending' ? (
                        <CountdownTimer expiresAt={item.expires_at} />
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-5 py-3" onClick={(e) => e.stopPropagation()}>
                      {item.status === 'pending' && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleResolve(item.id, 'approve')}
                            disabled={resolving === item.id}
                            className="px-3 py-1 rounded bg-green-500/10 text-green-400 text-xs font-medium hover:bg-green-500/20 transition-colors disabled:opacity-50"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleResolve(item.id, 'reject')}
                            disabled={resolving === item.id}
                            className="px-3 py-1 rounded bg-red-500/10 text-red-400 text-xs font-medium hover:bg-red-500/20 transition-colors disabled:opacity-50"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-[#1a1a1d]">
            <span className="text-sm text-gray-400">
              Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, data?.total || 0)} of{' '}
              {data?.total || 0}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 0}
                className="px-3 py-1 text-sm rounded border border-[#1a1a1d] text-gray-300 hover:bg-[#1a1a1d] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages - 1}
                className="px-3 py-1 text-sm rounded border border-[#1a1a1d] text-gray-300 hover:bg-[#1a1a1d] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedApproval && (
        <ApprovalDrawer
          approval={selectedApproval}
          onClose={() => setSelectedApproval(null)}
          onResolve={handleResolve}
          resolving={resolving}
        />
      )}
    </div>
  )
}

// ── Detail Drawer ───────────────────────────────────────────────────

function ApprovalDrawer({
  approval,
  onClose,
  onResolve,
  resolving,
}: {
  approval: Approval
  onClose: () => void
  onResolve: (id: string, action: 'approve' | 'reject') => void
  resolving: string | null
}) {
  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-[#10131C] border-l border-[#1a1a1d] z-50 overflow-y-auto shadow-2xl flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-[#10131C]/95 backdrop-blur border-b border-[#1a1a1d] px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-lg font-semibold text-white">Approval Detail</h2>
            <p className="text-xs text-gray-500 font-mono mt-0.5">{approval.id}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-white rounded transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5"
            >
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 p-6 space-y-6">
          {/* Status + Actions */}
          <div className="flex items-center justify-between">
            <StatusBadge status={approval.status} large />
            {approval.status === 'pending' && (
              <div className="flex gap-2">
                <button
                  onClick={() => onResolve(approval.id, 'approve')}
                  disabled={resolving === approval.id}
                  className="px-4 py-2 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm font-medium hover:bg-green-500/20 transition-colors disabled:opacity-50"
                >
                  Approve
                </button>
                <button
                  onClick={() => onResolve(approval.id, 'reject')}
                  disabled={resolving === approval.id}
                  className="px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium hover:bg-red-500/20 transition-colors disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            )}
          </div>

          {/* Request Info */}
          <div className="bg-[#04070D] border border-[#1a1a1d] rounded-xl p-4 space-y-3 text-sm">
            <h3 className="text-gray-400 font-medium text-xs uppercase tracking-wider">Request</h3>
            <InfoRow label="Agent" value={approval.agent_name || approval.agent_id} />
            <InfoRow label="Endpoint" value={approval.endpoint} mono />
            <InfoRow label="Method" value={<MethodBadge method={approval.method} />} />
            <InfoRow label="Created" value={formatDateTime(approval.created_at)} />
            <InfoRow
              label="Expires"
              value={
                approval.status === 'pending' ? (
                  <CountdownTimer expiresAt={approval.expires_at} />
                ) : (
                  formatDateTime(approval.expires_at)
                )
              }
            />
          </div>

          {/* Reviewer Info (if resolved) */}
          {approval.resolved_at && (
            <div className="bg-[#04070D] border border-[#1a1a1d] rounded-xl p-4 space-y-3 text-sm">
              <h3 className="text-gray-400 font-medium text-xs uppercase tracking-wider">
                Resolution
              </h3>
              <InfoRow label="Decision" value={<StatusBadge status={approval.status} />} />
              <InfoRow label="Resolved at" value={formatDateTime(approval.resolved_at)} />
              {approval.reviewer_note && <InfoRow label="Note" value={approval.reviewer_note} />}
            </div>
          )}

          {/* Request Metadata */}
          {Object.keys(approval.request_metadata).length > 0 && (
            <div className="bg-[#04070D] border border-[#1a1a1d] rounded-xl p-4 space-y-3 text-sm">
              <h3 className="text-gray-400 font-medium text-xs uppercase tracking-wider">
                Metadata
              </h3>
              <pre className="text-xs text-gray-400 overflow-x-auto">
                {JSON.stringify(approval.request_metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ── Helper Components ───────────────────────────────────────────────

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string
  value: React.ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-400">{label}</span>
      <span className={`text-white ${mono ? 'font-mono text-xs' : ''}`}>{value}</span>
    </div>
  )
}

function StatusBadge({ status, large }: { status: string; large?: boolean }) {
  const map: Record<string, { bg: string; text: string; dot: string }> = {
    pending: {
      bg: 'bg-yellow-500/10 border-yellow-500/20',
      text: 'text-yellow-400',
      dot: 'bg-yellow-400',
    },
    approved: {
      bg: 'bg-green-500/10 border-green-500/20',
      text: 'text-green-400',
      dot: 'bg-green-400',
    },
    rejected: {
      bg: 'bg-red-500/10 border-red-500/20',
      text: 'text-red-400',
      dot: 'bg-red-400',
    },
    expired: {
      bg: 'bg-gray-500/10 border-gray-500/20',
      text: 'text-gray-400',
      dot: 'bg-gray-400',
    },
  }
  const style = map[status] || map.expired
  const size = large ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-xs'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${style.bg} ${style.text} ${size}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: 'text-green-400',
    POST: 'text-[#A6DAFF]',
    PUT: 'text-yellow-400',
    PATCH: 'text-yellow-400',
    DELETE: 'text-red-400',
  }
  return (
    <span className={`font-mono text-xs font-medium ${colors[method] || 'text-gray-400'}`}>
      {method}
    </span>
  )
}

function PendingDot() {
  return (
    <span className="relative ml-1.5">
      <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
    </span>
  )
}

function CountdownTimer({ expiresAt }: { expiresAt: string }) {
  const [remaining, setRemaining] = useState('')
  const [isLow, setIsLow] = useState(false)

  useEffect(() => {
    const update = () => {
      const diff = new Date(expiresAt).getTime() - Date.now()
      if (diff <= 0) {
        setRemaining('Expired')
        setIsLow(true)
        return
      }
      const mins = Math.floor(diff / 60000)
      const secs = Math.floor((diff % 60000) / 1000)
      setRemaining(`${mins}m ${secs}s`)
      setIsLow(diff < 60000)
    }
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [expiresAt])

  return <span className={isLow ? 'text-red-400 font-medium' : 'text-gray-400'}>{remaining}</span>
}

// ── Formatters ──────────────────────────────────────────────────────

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}
