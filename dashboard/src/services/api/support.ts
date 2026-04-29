/**
 * Support ticket API client functions.
 */

import { apiFetch, toQueryString } from './client'
import type {
  CommentCreate,
  TicketComment,
  TicketContextResponse,
  TicketCreate,
  TicketDetail,
  TicketListResponse,
  TicketUpdate,
} from '@/types/api'

/**
 * Create a new support ticket.
 */
export async function createTicket(data: TicketCreate): Promise<TicketDetail> {
  return apiFetch('/api/v1/tickets', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/**
 * List support tickets with optional filtering.
 */
export async function listTickets(params?: {
  status?: string
  priority?: string
  category?: string
  assigned_to_me?: boolean
  limit?: number
  offset?: number
}): Promise<TicketListResponse> {
  const query = params ? `?${toQueryString(params)}` : ''
  return apiFetch(`/api/v1/tickets${query}`)
}

/**
 * Get full details of a support ticket including comments.
 */
export async function getTicket(ticketId: string): Promise<TicketDetail> {
  return apiFetch(`/api/v1/tickets/${ticketId}`)
}

/**
 * Update a support ticket.
 */
export async function updateTicket(ticketId: string, data: TicketUpdate): Promise<TicketDetail> {
  return apiFetch(`/api/v1/tickets/${ticketId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

/**
 * Add a comment to a support ticket.
 */
export async function addComment(ticketId: string, data: CommentCreate): Promise<TicketComment> {
  return apiFetch(`/api/v1/tickets/${ticketId}/comments`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/**
 * Get related context for a ticket (agent details, audit logs, org info).
 */
export async function getTicketContext(ticketId: string): Promise<TicketContextResponse> {
  return apiFetch(`/api/v1/tickets/${ticketId}/context`)
}

// Made with Bob
