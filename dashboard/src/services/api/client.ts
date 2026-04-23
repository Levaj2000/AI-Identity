/**
 * Base API client — typed fetch wrapper with Clerk JWT auth.
 *
 * Auth: Uses Clerk session tokens sent as Bearer authorization.
 * All /api/* requests get the Authorization header automatically.
 * /health is public and skips auth.
 */

import type { ApiError, ValidationErrorItem, ValidationErrorResponse } from '../../types/api'

// ─── Config ──────────────────────────────────────────────────────

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || ''

// ─── Session token management ────────────────────────────────────

/** Function that returns a Clerk session token (set by AuthProvider). */
let getSessionToken: (() => Promise<string | null>) | null = null

/** Register the Clerk session token getter. Called by AuthProvider. */
export function setSessionTokenGetter(getter: () => Promise<string | null>): void {
  getSessionToken = getter
}

/** Clear the session token getter (on logout). */
export function clearSessionTokenGetter(): void {
  getSessionToken = null
}

// ─── Legacy API key support (for backward compat during migration) ──

const STORAGE_KEY = 'ai-identity-api-key'

export function getApiKey(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(STORAGE_KEY) || ''
  }
  return ''
}

export function setApiKey(key: string): void {
  localStorage.setItem(STORAGE_KEY, key)
}

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
  let validationErrors: ValidationErrorItem[] | undefined

  try {
    const body = await response.json()

    // FastAPI validation errors → join messages + preserve raw items
    if (Array.isArray(body.detail)) {
      const validation = body as ValidationErrorResponse
      message = validation.detail.map((e) => `${e.loc.join('.')}: ${e.msg}`).join('; ')
      code = 'VALIDATION_ERROR'
      validationErrors = validation.detail
    } else if (typeof body.detail === 'string') {
      message = body.detail
      code = body.code || 'API_ERROR'
    } else if (body.message) {
      message = body.message
      code = body.code || 'API_ERROR'
    } else if (body.error && typeof body.error === 'object') {
      // Canonical API error envelope from our backend:
      //   { "error": { "code": "some_stable_code", "message": "..." } }
      // Used by the app-wide http_exception_handler and by any
      // JSONResponse-returning endpoint that wants to keep its code
      // intact (compliance exports, rate-limit 429s, etc).
      if (typeof body.error.message === 'string') {
        message = body.error.message
      }
      if (typeof body.error.code === 'string') {
        code = body.error.code
      }
    }
  } catch {
    // Response body wasn't JSON — keep defaults
  }

  return { status: response.status, code, message, validationErrors }
}

// ─── Core fetch ──────────────────────────────────────────────────

/**
 * Typed fetch wrapper.
 *
 * - Prepends API_BASE_URL
 * - Injects Authorization: Bearer <token> for /api/* routes (Clerk JWT)
 * - Falls back to X-API-Key if no Clerk session (backward compat)
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
    // Try Clerk session token first (preferred)
    if (getSessionToken) {
      const token = await getSessionToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }

    // Fall back to legacy X-API-Key if no Bearer token
    if (!headers['Authorization']) {
      const key = getApiKey()
      if (key) {
        headers['X-API-Key'] = key
      }
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

// ─── Auth header helper (for raw fetch calls like blob downloads) ──

/**
 * Build the auth headers that apiFetch would inject.
 * Use this when you need raw fetch() (e.g. blob downloads) but still
 * need authentication.
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {}
  if (getSessionToken) {
    const token = await getSessionToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
  }
  if (!headers['Authorization']) {
    const key = getApiKey()
    if (key) {
      headers['X-API-Key'] = key
    }
  }
  return headers
}

/** Return the configured API base URL. */
export function getApiBaseUrl(): string {
  return API_BASE_URL
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
