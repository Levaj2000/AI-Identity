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
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
      case 'high':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
      case 'low':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
      case 'in_progress':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400'
      case 'waiting_customer':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
      case 'resolved':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
      case 'closed':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
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
        <div className="text-gray-600 dark:text-[#a1a1aa]">Loading ticket...</div>
      </div>
    )
  }

  if (error || !ticket) {
    return (
      <div>
        <button
          onClick={() => navigate('/dashboard/support')}
          className="mb-4 text-sm text-[#A6DAFF] hover:underline"
        >
          ← Back to tickets
        </button>
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-400">
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
        className="mb-4 text-sm text-[#A6DAFF] hover:underline"
      >
        ← Back to tickets
      </button>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Content - Ticket Details & Comments */}
        <div className="lg:col-span-2 space-y-6">
          {/* Ticket Header */}
          <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-[#27272a] dark:bg-[#09090b]">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-mono text-gray-500 dark:text-[#71717a]">
                    {ticket.ticket_number}
                  </span>
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
                <h1 className="text-2xl font-bold text-gray-900 dark:text-[#e4e4e7]">
                  {ticket.subject}
                </h1>
              </div>
            </div>

            <div className="prose prose-sm dark:prose-invert max-w-none">
              <p className="text-gray-700 dark:text-[#a1a1aa] whitespace-pre-wrap">
                {ticket.description}
              </p>
            </div>

            <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-600 dark:text-[#a1a1aa]">
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
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-[#27272a]">
                <label className="block text-sm font-medium text-gray-700 dark:text-[#e4e4e7] mb-2">
                  Update Status
                </label>
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
                          ? 'bg-gray-200 text-gray-500 cursor-not-allowed dark:bg-gray-800'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-[#27272a] dark:text-[#e4e4e7] dark:hover:bg-[#3a3a3d]'
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
          <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-[#27272a] dark:bg-[#09090b]">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7] mb-4">
              Comments ({ticket.comments.length})
            </h2>

            {/* Comments List */}
            <div className="space-y-4 mb-6">
              {ticket.comments.length === 0 ? (
                <p className="text-sm text-gray-600 dark:text-[#a1a1aa]">
                  No comments yet. Be the first to comment!
                </p>
              ) : (
                ticket.comments.map((comment) => (
                  <div
                    key={comment.id}
                    className={`rounded-lg p-4 ${
                      comment.is_internal
                        ? 'bg-yellow-50 border border-yellow-200 dark:bg-yellow-900/10 dark:border-yellow-900/30'
                        : 'bg-gray-50 dark:bg-[#1a1a1d]'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-[#e4e4e7]">
                          {comment.user_email}
                        </span>
                        {comment.is_internal && (
                          <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                            Internal
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-gray-500 dark:text-[#71717a]">
                        {formatDate(comment.created_at)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 dark:text-[#a1a1aa] whitespace-pre-wrap">
                      {comment.content}
                    </p>
                  </div>
                ))
              )}
            </div>

            {/* Add Comment Form */}
            {ticket.status !== 'closed' && (
              <form
                onSubmit={handleAddComment}
                className="border-t border-gray-200 pt-4 dark:border-[#27272a]"
              >
                <label
                  htmlFor="comment"
                  className="block text-sm font-medium text-gray-700 dark:text-[#e4e4e7] mb-2"
                >
                  Add Comment
                </label>
                <textarea
                  id="comment"
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  rows={4}
                  className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 focus:border-[#A6DAFF] focus:outline-none focus:ring-1 focus:ring-[#A6DAFF] dark:border-[#27272a] dark:bg-[#09090b] dark:text-[#e4e4e7]"
                  placeholder="Type your comment here..."
                />
                <div className="mt-3 flex justify-end">
                  <button
                    type="submit"
                    disabled={isSubmittingComment || !commentText.trim()}
                    className="rounded-lg bg-[#A6DAFF] px-4 py-2 text-sm font-medium text-gray-900 hover:bg-[#8fc7ff] disabled:opacity-50"
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
          <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-[#27272a] dark:bg-[#09090b]">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-[#e4e4e7] mb-3">
              Ticket Information
            </h3>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-gray-600 dark:text-[#a1a1aa]">Category</dt>
                <dd className="font-medium text-gray-900 dark:text-[#e4e4e7]">
                  {ticket.category ? ticket.category.replace(/_/g, ' ') : 'None'}
                </dd>
              </div>
              <div>
                <dt className="text-gray-600 dark:text-[#a1a1aa]">Created By</dt>
                <dd className="font-medium text-gray-900 dark:text-[#e4e4e7]">
                  {ticket.user_email}
                </dd>
              </div>
              {ticket.org_name && (
                <div>
                  <dt className="text-gray-600 dark:text-[#a1a1aa]">Organization</dt>
                  <dd className="font-medium text-gray-900 dark:text-[#e4e4e7]">
                    {ticket.org_name}
                  </dd>
                </div>
              )}
              {ticket.assigned_to_email && (
                <div>
                  <dt className="text-gray-600 dark:text-[#a1a1aa]">Assigned To</dt>
                  <dd className="font-medium text-gray-900 dark:text-[#e4e4e7]">
                    {ticket.assigned_to_email}
                  </dd>
                </div>
              )}
            </dl>
          </div>

          {/* Related Agent */}
          {context?.related_agent && (
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-[#27272a] dark:bg-[#09090b]">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-[#e4e4e7] mb-3">
                Related Agent
              </h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-gray-900 dark:text-[#e4e4e7]">
                    {context.related_agent.name}
                  </span>
                </div>
                <div className="text-gray-600 dark:text-[#a1a1aa]">
                  Status: {context.related_agent.status}
                </div>
                <button
                  onClick={() => navigate(`/dashboard/agents/${context.related_agent?.id}`)}
                  className="text-[#A6DAFF] hover:underline text-sm"
                >
                  View Agent →
                </button>
              </div>
            </div>
          )}

          {/* Recent Audit Logs */}
          {context?.recent_audit_logs && context.recent_audit_logs.length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-[#27272a] dark:bg-[#09090b]">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-[#e4e4e7] mb-3">
                Related Audit Logs
              </h3>
              <div className="space-y-2">
                {context.recent_audit_logs.slice(0, 5).map((log) => (
                  <div key={log.id} className="text-xs">
                    <div className="font-medium text-gray-900 dark:text-[#e4e4e7]">
                      {log.action}
                    </div>
                    <div className="text-gray-600 dark:text-[#a1a1aa]">
                      {new Date(log.timestamp).toLocaleString()}
                    </div>
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
