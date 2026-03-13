/**
 * Base API client — typed fetch wrapper with X-API-Key auth.
 *
 * Auth priority:
 *   1. localStorage key "ai-identity-api-key" (set by dashboard UI)
 *   2. VITE_API_KEY env var (dev fallback)
 *
 * All /api/* requests get the X-API-Key header automatically.
 * /health is public and skips auth.
 */

import type { ApiError, ValidationErrorResponse } from '../../types/api'

// ─── Config ──────────────────────────────────────────────────────

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || ''

const STORAGE_KEY = 'ai-identity-api-key'

/** Read API key from localStorage, fall back to env var. */
export function getApiKey(): string {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return stored
  }
  return import.meta.env.VITE_API_KEY || ''
}

/** Persist API key to localStorage (used by settings/onboarding). */
export function setApiKey(key: string): void {
  localStorage.setItem(STORAGE_KEY, key)
}

/** Clear stored API key. */
export function clearApiKey(): void {
  localStorage.removeItem(STORAGE_KEY)
}

// ─── Error helpers ───────────────────────────────────────────────

/** Type guard: is this a structured ApiError thrown by apiFetch? */
export function isApiError(err: unknown): err is ApiError {
  return (
    typeof err === 'object' && err !== null && 'status' in err && 'code' in err && 'message' in err
  )
}

/** Parse a non-OK response into a typed ApiError. */
export async function parseErrorResponse(response: Response): Promise<ApiError> {
  let message = response.statusText || 'Request failed'
  let code = 'UNKNOWN'

  try {
    const body = await response.json()

    // FastAPI validation errors → join messages
    if (Array.isArray(body.detail)) {
      const validation = body as ValidationErrorResponse
      message = validation.detail.map((e) => `${e.loc.join('.')}: ${e.msg}`).join('; ')
      code = 'VALIDATION_ERROR'
    } else if (typeof body.detail === 'string') {
      message = body.detail
      code = body.code || 'API_ERROR'
    } else if (body.message) {
      message = body.message
      code = body.code || 'API_ERROR'
    }
  } catch {
    // Response body wasn't JSON — keep defaults
  }

  return { status: response.status, code, message }
}

// ─── Core fetch ──────────────────────────────────────────────────

/**
 * Typed fetch wrapper.
 *
 * - Prepends API_BASE_URL
 * - Injects X-API-Key for /api/* routes
 * - Sets Content-Type: application/json for requests with body
 * - Parses JSON response
 * - Throws typed ApiError on non-2xx
 */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }

  // Only set Content-Type for requests that have a body
  if (options.body) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json'
  }

  // Inject auth for API routes (skip for /health which is public)
  if (path.startsWith('/api/')) {
    const key = getApiKey()
    if (key) {
      headers['X-API-Key'] = key
    }
  }

  const response = await fetch(url, { ...options, headers })

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

// ─── Query string helper ─────────────────────────────────────────

/** Build a query string from an object, omitting undefined/null values. */
export function toQueryString(
  params: Record<string, string | number | boolean | undefined | null>,
): string {
  const entries = Object.entries(params).filter(
    (entry): entry is [string, string | number | boolean] => entry[1] != null,
  )
  if (entries.length === 0) return ''
  return '?' + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()
}
