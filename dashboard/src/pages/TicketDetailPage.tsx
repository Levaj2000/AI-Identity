/**
 * Ticket Detail Page - Full ticket view with comments and context
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTicket, addComment, updateTicket, getTicketContext } from '../services/api'
import type { TicketDetail, TicketContextResponse, TicketStatus } from '../types/api'
import { useAuth } from '../hooks/useAuth'

export function TicketDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [ticket, setTicket] = useState<TicketDetail | null>(null)
  const [context, setContext] = useState<TicketContextResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Comment form
  const [commentText, setCommentText] = useState('')
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)

  // Status update
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false)

  const loadTicket = async () => {
    if (!id) return

    setIsLoading(true)
    setError(null)
    try {
      const [ticketData, contextData] = await Promise.all([
        getTicket(id),
        getTicketContext(id).catch(() => null), // Context is optional
      ])
      setTicket(ticketData)
      setContext(contextData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ticket')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadTicket()
  }, [id])

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !commentText.trim()) return

    setIsSubmittingComment(true)
    try {
      await addComment(id, { content: commentText })
      setCommentText('')
      await loadTicket() // Reload to show new comment
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add comment')
    } finally {
      setIsSubmittingComment(false)
    }
  }

  const handleStatusChange = async (newStatus: TicketStatus) => {
    if (!id) return

    setIsUpdatingStatus(true)
    try {
      await updateTicket(id, { status: newStatus })
      await loadTicket() // Reload to show updated status
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update status')
    } finally {
      setIsUpdatingStatus(false)
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'bg-danger-soft text-danger'
      case 'high':
        return 'bg-anomaly-soft text-anomaly'
      case 'medium':
        return 'bg-warning-soft text-warning'
      case 'low':
        return 'bg-success-soft text-success'
      default:
        return 'bg-elevated text-muted'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-brand-soft text-brand'
      case 'in_progress':
        return 'bg-ai-soft text-ai'
      case 'waiting_customer':
        return 'bg-warning-soft text-warning'
      case 'resolved':
        return 'bg-success-soft text-success'
      case 'closed':
        return 'bg-elevated text-muted'
      default:
        return 'bg-elevated text-muted'
    }
  }

  const formatStatus = (status: string) => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted">Loading ticket...</div>
      </div>
    )
  }

  if (error || !ticket) {
    return (
      <div>
        <button
          onClick={() => navigate('/dashboard/support')}
          className="mb-4 text-sm text-brand hover:underline"
        >
          ← Back to tickets
        </button>
        <div className="rounded-lg bg-danger-soft p-4 text-sm text-danger">
          {error || 'Ticket not found'}
        </div>
      </div>
    )
  }

  const isAdmin = user?.role === 'admin'

  return (
    <div>
      {/* Back Button */}
      <button
        onClick={() => navigate('/dashboard/support')}
        className="mb-4 text-sm text-brand hover:underline"
      >
        ← Back to tickets
      </button>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Content - Ticket Details & Comments */}
        <div className="lg:col-span-2 space-y-6">
          {/* Ticket Header */}
          <div className="rounded-lg border border-line bg-surface p-6">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-mono text-subtle">{ticket.ticket_number}</span>
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${getStatusColor(ticket.status)}`}
                  >
                    {formatStatus(ticket.status)}
                  </span>
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${getPriorityColor(ticket.priority)}`}
                  >
                    {ticket.priority.toUpperCase()}
                  </span>
                </div>
                <h1 className="text-2xl font-bold text-ink">{ticket.subject}</h1>
              </div>
            </div>

            <div className="prose prose-sm dark:prose-invert max-w-none">
              <p className="text-muted whitespace-pre-wrap">{ticket.description}</p>
            </div>

            <div className="mt-4 flex flex-wrap gap-4 text-sm text-muted">
              <div>
                <span className="font-medium">Created:</span> {formatDate(ticket.created_at)}
              </div>
              <div>
                <span className="font-medium">Updated:</span> {formatDate(ticket.updated_at)}
              </div>
              {ticket.resolved_at && (
                <div>
                  <span className="font-medium">Resolved:</span> {formatDate(ticket.resolved_at)}
                </div>
              )}
            </div>

            {/* Admin Status Controls */}
            {isAdmin && ticket.status !== 'closed' && (
              <div className="mt-4 pt-4 border-t border-line">
                <label className="block text-sm font-medium text-muted mb-2">Update Status</label>
                <div className="flex flex-wrap gap-2">
                  {(
                    [
                      'open',
                      'in_progress',
                      'waiting_customer',
                      'resolved',
                      'closed',
                    ] as TicketStatus[]
                  ).map((status) => (
                    <button
                      key={status}
                      onClick={() => handleStatusChange(status)}
                      disabled={isUpdatingStatus || ticket.status === status}
                      className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                        ticket.status === status
                          ? 'bg-elevated text-subtle cursor-not-allowed'
                          : 'bg-elevated text-muted hover:bg-inset'
                      }`}
                    >
                      {formatStatus(status)}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Comments Section */}
          <div className="rounded-lg border border-line bg-surface p-6">
            <h2 className="text-lg font-semibold text-ink mb-4">
              Comments ({ticket.comments.length})
            </h2>

            {/* Comments List */}
            <div className="space-y-4 mb-6">
              {ticket.comments.length === 0 ? (
                <p className="text-sm text-muted">No comments yet. Be the first to comment!</p>
              ) : (
                ticket.comments.map((comment) => (
                  <div
                    key={comment.id}
                    className={`rounded-lg p-4 ${
                      comment.is_internal ? 'bg-warning-soft border border-warning' : 'bg-inset'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-ink">{comment.user_email}</span>
                        {comment.is_internal && (
                          <span className="inline-flex items-center rounded-full bg-warning-soft px-2 py-0.5 text-xs font-medium text-warning">
                            Internal
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-subtle">{formatDate(comment.created_at)}</span>
                    </div>
                    <p className="text-sm text-muted whitespace-pre-wrap">{comment.content}</p>
                  </div>
                ))
              )}
            </div>

            {/* Add Comment Form */}
            {ticket.status !== 'closed' && (
              <form onSubmit={handleAddComment} className="border-t border-line pt-4">
                <label htmlFor="comment" className="block text-sm font-medium text-muted mb-2">
                  Add Comment
                </label>
                <textarea
                  id="comment"
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  rows={4}
                  className="block w-full rounded-lg border border-line-strong bg-inset px-3 py-2 text-ink focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
                  placeholder="Type your comment here..."
                />
                <div className="mt-3 flex justify-end">
                  <button
                    type="submit"
                    disabled={isSubmittingComment || !commentText.trim()}
                    className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-ink hover:bg-brand-hover disabled:opacity-50"
                  >
                    {isSubmittingComment ? 'Posting...' : 'Post Comment'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>

        {/* Sidebar - Context & Metadata */}
        <div className="space-y-6">
          {/* Ticket Info */}
          <div className="rounded-lg border border-line bg-surface p-4">
            <h3 className="text-sm font-semibold text-ink mb-3">Ticket Information</h3>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-muted">Category</dt>
                <dd className="font-medium text-ink">
                  {ticket.category ? ticket.category.replace(/_/g, ' ') : 'None'}
                </dd>
              </div>
              <div>
                <dt className="text-muted">Created By</dt>
                <dd className="font-medium text-ink">{ticket.user_email}</dd>
              </div>
              {ticket.org_name && (
                <div>
                  <dt className="text-muted">Organization</dt>
                  <dd className="font-medium text-ink">{ticket.org_name}</dd>
                </div>
              )}
              {ticket.assigned_to_email && (
                <div>
                  <dt className="text-muted">Assigned To</dt>
                  <dd className="font-medium text-ink">{ticket.assigned_to_email}</dd>
                </div>
              )}
            </dl>
          </div>

          {/* Related Agent */}
          {context?.related_agent && (
            <div className="rounded-lg border border-line bg-surface p-4">
              <h3 className="text-sm font-semibold text-ink mb-3">Related Agent</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-ink">{context.related_agent.name}</span>
                </div>
                <div className="text-muted">Status: {context.related_agent.status}</div>
                <button
                  onClick={() => navigate(`/dashboard/agents/${context.related_agent?.id}`)}
                  className="text-brand hover:underline text-sm"
                >
                  View Agent →
                </button>
              </div>
            </div>
          )}

          {/* Recent Audit Logs */}
          {context?.recent_audit_logs && context.recent_audit_logs.length > 0 && (
            <div className="rounded-lg border border-line bg-surface p-4">
              <h3 className="text-sm font-semibold text-ink mb-3">Related Audit Logs</h3>
              <div className="space-y-2">
                {context.recent_audit_logs.slice(0, 5).map((log) => (
                  <div key={log.id} className="text-xs">
                    <div className="font-medium text-ink">{log.action}</div>
                    <div className="text-muted">{new Date(log.timestamp).toLocaleString()}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Made with Bob
