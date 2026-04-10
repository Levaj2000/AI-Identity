import { useCallback, useEffect, useReducer, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listAgents } from '../services/api/agents'
import { isApiError } from '../services/api/client'
import { useDebounce } from './useDebounce'
import type { Agent, AgentStatus, ApiError } from '../types/api'

const PAGE_SIZE = 20
const DEBOUNCE_MS = 300

const VALID_STATUSES: AgentStatus[] = ['active', 'suspended', 'revoked']

function parseStatus(value: string | null): AgentStatus | undefined {
  if (value && VALID_STATUSES.includes(value as AgentStatus)) {
    return value as AgentStatus
  }
  return undefined
}

function parsePage(value: string | null): number {
  const n = Number(value)
  return n >= 1 ? Math.floor(n) : 1
}

// ─── Data reducer (avoids synchronous setState in effects) ──

interface DataState {
  agents: Agent[]
  total: number
  isLoading: boolean
  error: ApiError | null
}

type DataAction =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; agents: Agent[]; total: number }
  | { type: 'FETCH_ERROR'; error: ApiError }

function dataReducer(state: DataState, action: DataAction): DataState {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, isLoading: true, error: null }
    case 'FETCH_SUCCESS':
      return { agents: action.agents, total: action.total, isLoading: false, error: null }
    case 'FETCH_ERROR':
      return { ...state, isLoading: false, error: action.error }
  }
}

const INITIAL_STATE: DataState = {
  agents: [],
  total: 0,
  isLoading: true,
  error: null,
}

// ─── Return type ──────────────────────────────────────────────

interface UseAgentsListReturn extends DataState {
  // Filters
  statusFilter: AgentStatus | undefined
  setStatusFilter: (status: AgentStatus | undefined) => void
  capabilityFilter: string
  setCapabilityFilter: (cap: string) => void
  // Pagination
  page: number
  setPage: (p: number) => void
  totalPages: number
  pageSize: number
  // Manual refresh
  refetch: () => void
}

// ─── Hook ─────────────────────────────────────────────────────

/**
 * Data hook for the Agents list page.
 *
 * Manages status/capability filters, pagination, and URL search params.
 * Fetches agents via `listAgents()` and re-fetches when filters or page change.
 */
export function useAgentsList(): UseAgentsListReturn {
  const [searchParams, setSearchParams] = useSearchParams()

  // Read initial values from URL
  const [statusFilter, setStatusFilterState] = useState<AgentStatus | undefined>(
    parseStatus(searchParams.get('status')),
  )
  const [capabilityFilter, setCapabilityFilterState] = useState(
    searchParams.get('capability') || '',
  )
  const [page, setPageState] = useState(parsePage(searchParams.get('page')))

  // Debounce capability input
  const debouncedCapability = useDebounce(capabilityFilter, DEBOUNCE_MS)

  // Data state via reducer (avoids synchronous setState in effects)
  const [data, dispatch] = useReducer(dataReducer, INITIAL_STATE)
  const [refreshKey, setRefreshKey] = useState(0)
  const refetch = useCallback(() => setRefreshKey((k) => k + 1), [])

  // ── Setters that also update URL params ───────────────────

  const setStatusFilter = useCallback(
    (status: AgentStatus | undefined) => {
      setStatusFilterState(status)
      setPageState(1) // Reset to page 1 on filter change
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (status) {
            next.set('status', status)
          } else {
            next.delete('status')
          }
          next.delete('page') // Reset page
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const setCapabilityFilter = useCallback((cap: string) => {
    setCapabilityFilterState(cap)
    setPageState(1) // Reset to page 1 on filter change
  }, [])

  const setPage = useCallback(
    (p: number) => {
      setPageState(p)
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (p > 1) {
            next.set('page', String(p))
          } else {
            next.delete('page')
          }
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  // ── Sync debounced capability to URL ──────────────────────

  useEffect(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (debouncedCapability) {
          next.set('capability', debouncedCapability)
        } else {
          next.delete('capability')
        }
        next.delete('page') // Reset page on capability change
        return next
      },
      { replace: true },
    )
  }, [debouncedCapability, setSearchParams])

  // ── Fetch agents ──────────────────────────────────────────

  useEffect(() => {
    let cancelled = false
    dispatch({ type: 'FETCH_START' })

    const offset = (page - 1) * PAGE_SIZE

    listAgents({
      status: statusFilter,
      capability: debouncedCapability || undefined,
      limit: PAGE_SIZE,
      offset,
    })
      .then((result) => {
        if (!cancelled) {
          dispatch({ type: 'FETCH_SUCCESS', agents: result.items, total: result.total })
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          dispatch({
            type: 'FETCH_ERROR',
            error: isApiError(err)
              ? err
              : { status: 0, code: 'NETWORK_ERROR', message: String(err) },
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [statusFilter, debouncedCapability, page, refreshKey])

  return {
    ...data,
    statusFilter,
    setStatusFilter,
    capabilityFilter,
    setCapabilityFilter,
    page,
    setPage,
    totalPages: Math.max(1, Math.ceil(data.total / PAGE_SIZE)),
    pageSize: PAGE_SIZE,
    refetch,
  }
}
