/**
 * Support Tickets Page - List view of all support tickets with filtering
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listTickets } from '../services/api'
import { CreateTicketModal } from '../components/modals/CreateTicketModal'
import type { SupportTicket, TicketPriority, TicketStatus, TicketCategory } from '../types/api'

export function SupportTicketsPage() {
  const navigate = useNavigate()
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  // Filters
  const [statusFilter, setStatusFilter] = useState<TicketStatus | ''>('')
  const [priorityFilter, setPriorityFilter] = useState<TicketPriority | ''>('')
  const [categoryFilter, setCategoryFilter] = useState<TicketCategory | ''>('')

  const loadTickets = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await listTickets({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        category: categoryFilter || undefined,
        limit: 50,
      })
      setTickets(response.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tickets')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadTickets()
  }, [statusFilter, priorityFilter, categoryFilter])

  const getPriorityColor = (priority: TicketPriority) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
      case 'high':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
      case 'low':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
    }
  }

  const getStatusColor = (status: TicketStatus) => {
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
    }
  }

  const formatStatus = (status: TicketStatus) => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-[#e4e4e7]">Support Tickets</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-[#a1a1aa]">
            View and manage your support tickets
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="rounded-lg bg-[#A6DAFF] px-4 py-2 text-sm font-medium text-gray-900 hover:bg-[#8fc7ff]"
        >
          Create Ticket
        </button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap gap-4">
        <div>
          <label
            htmlFor="status"
            className="block text-xs font-medium text-gray-700 dark:text-[#e4e4e7] mb-1"
          >
            Status
          </label>
          <select
            id="status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as TicketStatus | '')}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-900 focus:border-[#A6DAFF] focus:outline-none focus:ring-1 focus:ring-[#A6DAFF] dark:border-[#27272a] dark:bg-[#09090b] dark:text-[#e4e4e7]"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="waiting_customer">Waiting Customer</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="priority"
            className="block text-xs font-medium text-gray-700 dark:text-[#e4e4e7] mb-1"
          >
            Priority
          </label>
          <select
            id="priority"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as TicketPriority | '')}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-900 focus:border-[#A6DAFF] focus:outline-none focus:ring-1 focus:ring-[#A6DAFF] dark:border-[#27272a] dark:bg-[#09090b] dark:text-[#e4e4e7]"
          >
            <option value="">All Priorities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="category"
            className="block text-xs font-medium text-gray-700 dark:text-[#e4e4e7] mb-1"
          >
            Category
          </label>
          <select
            id="category"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as TicketCategory | '')}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-900 focus:border-[#A6DAFF] focus:outline-none focus:ring-1 focus:ring-[#A6DAFF] dark:border-[#27272a] dark:bg-[#09090b] dark:text-[#e4e4e7]"
          >
            <option value="">All Categories</option>
            <option value="technical">Technical</option>
            <option value="billing">Billing</option>
            <option value="feature_request">Feature Request</option>
            <option value="bug">Bug</option>
            <option value="other">Other</option>
          </select>
        </div>

        {(statusFilter || priorityFilter || categoryFilter) && (
          <button
            onClick={() => {
              setStatusFilter('')
              setPriorityFilter('')
              setCategoryFilter('')
            }}
            className="self-end rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-[#27272a] dark:text-[#e4e4e7] dark:hover:bg-[#27272a]"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-gray-600 dark:text-[#a1a1aa]">Loading tickets...</div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Tickets List */}
      {!isLoading && !error && (
        <div className="space-y-3">
          {tickets.length === 0 ? (
            <div className="rounded-lg border border-gray-200 bg-white p-12 text-center dark:border-[#27272a] dark:bg-[#09090b]">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                />
              </svg>
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-[#e4e4e7]">
                No tickets found
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-[#a1a1aa]">
                {statusFilter || priorityFilter || categoryFilter
                  ? 'Try adjusting your filters'
                  : 'Create your first support ticket to get started'}
              </p>
            </div>
          ) : (
            tickets.map((ticket) => (
              <div
                key={ticket.id}
                onClick={() => navigate(`/dashboard/support/${ticket.id}`)}
                className="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-[#A6DAFF] hover:bg-gray-50 dark:border-[#27272a] dark:bg-[#09090b] dark:hover:border-[#A6DAFF] dark:hover:bg-[#1a1a1d]"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
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
                      {ticket.category && (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-800 dark:bg-gray-800 dark:text-gray-300">
                          {ticket.category.replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                    <h3 className="text-base font-semibold text-gray-900 dark:text-[#e4e4e7] mb-1">
                      {ticket.subject}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-[#a1a1aa] line-clamp-2">
                      {ticket.description}
                    </p>
                    <div className="mt-2 flex items-center gap-4 text-xs text-gray-500 dark:text-[#71717a]">
                      <span>Created {formatDate(ticket.created_at)}</span>
                      {ticket.comment_count > 0 && (
                        <span className="flex items-center gap-1">
                          <svg
                            className="h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                            />
                          </svg>
                          {ticket.comment_count}
                        </span>
                      )}
                      {ticket.related_agent_name && (
                        <span className="flex items-center gap-1">
                          <svg
                            className="h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M13 10V3L4 14h7v7l9-11h-7z"
                            />
                          </svg>
                          {ticket.related_agent_name}
                        </span>
                      )}
                    </div>
                  </div>
                  <svg
                    className="h-5 w-5 text-gray-400 flex-shrink-0 ml-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Create Ticket Modal */}
      <CreateTicketModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={loadTickets}
      />
    </div>
  )
}

// Made with Bob
