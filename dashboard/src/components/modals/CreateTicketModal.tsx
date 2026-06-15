/**
 * CreateTicketModal - Form to create a new support ticket
 */

import { useState } from 'react'
import { createTicket } from '../../services/api'
import type { TicketCategory, TicketPriority } from '../../types/api'

interface CreateTicketModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function CreateTicketModal({ isOpen, onClose, onSuccess }: CreateTicketModalProps) {
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<TicketPriority>('medium')
  const [category, setCategory] = useState<TicketCategory>('technical')
  const [relatedAgentId, setRelatedAgentId] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await createTicket({
        subject,
        description,
        priority,
        category,
        related_agent_id: relatedAgentId || undefined,
      })

      // Reset form
      setSubject('')
      setDescription('')
      setPriority('medium')
      setCategory('technical')
      setRelatedAgentId('')

      onSuccess()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create ticket')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-2xl rounded-lg bg-surface p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-ink">Create Support Ticket</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-faint hover:bg-elevated hover:text-muted"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Subject */}
          <div>
            <label htmlFor="subject" className="block text-sm font-medium text-muted">
              Subject *
            </label>
            <input
              type="text"
              id="subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
              minLength={5}
              maxLength={255}
              className="mt-1 block w-full rounded-lg border border-line-strong bg-inset px-3 py-2 text-ink focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
              placeholder="Brief description of the issue"
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-muted">
              Description *
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              minLength={10}
              rows={6}
              className="mt-1 block w-full rounded-lg border border-line-strong bg-inset px-3 py-2 text-ink focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
              placeholder="Detailed description of the issue, steps to reproduce, expected vs actual behavior..."
            />
          </div>

          {/* Priority and Category */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="priority" className="block text-sm font-medium text-muted">
                Priority
              </label>
              <select
                id="priority"
                value={priority}
                onChange={(e) => setPriority(e.target.value as TicketPriority)}
                className="mt-1 block w-full rounded-lg border border-line-strong bg-inset px-3 py-2 text-ink focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div>
              <label htmlFor="category" className="block text-sm font-medium text-muted">
                Category
              </label>
              <select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value as TicketCategory)}
                className="mt-1 block w-full rounded-lg border border-line-strong bg-inset px-3 py-2 text-ink focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
              >
                <option value="technical">Technical Issue</option>
                <option value="billing">Billing</option>
                <option value="feature_request">Feature Request</option>
                <option value="bug">Bug Report</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          {/* Related Agent (Optional) */}
          <div>
            <label htmlFor="relatedAgent" className="block text-sm font-medium text-muted">
              Related Agent ID (Optional)
            </label>
            <input
              type="text"
              id="relatedAgent"
              value={relatedAgentId}
              onChange={(e) => setRelatedAgentId(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-line-strong bg-inset px-3 py-2 text-ink focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
              placeholder="Link this ticket to a specific agent"
            />
            <p className="mt-1 text-xs text-subtle">
              If this issue is related to a specific agent, paste its ID here
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg bg-danger-soft p-3 text-sm text-danger">{error}</div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-lg border border-line-strong px-4 py-2 text-sm font-medium text-muted hover:bg-elevated disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-ink hover:bg-brand-hover disabled:opacity-50"
            >
              {isSubmitting ? 'Creating...' : 'Create Ticket'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Made with Bob
