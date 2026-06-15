import { useReducer, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createAgent } from '../services/api/agents'
import { isApiError } from '../services/api/client'
import { CapabilitySelect } from '../components/forms/CapabilitySelect'
import { KeyValueEditor } from '../components/forms/KeyValueEditor'
import { ApiKeyModal } from '../components/modals/ApiKeyModal'
import type { AgentCreateResponse, ValidationErrorItem } from '../types/api'

// ─── Form state ─────────────────────────────────────────────────

interface KeyValueEntry {
  key: string
  value: string
}

interface FormState {
  name: string
  description: string
  capabilities: string[]
  metadataEntries: KeyValueEntry[]
}

type FormAction =
  | { type: 'SET_NAME'; value: string }
  | { type: 'SET_DESCRIPTION'; value: string }
  | { type: 'SET_CAPABILITIES'; value: string[] }
  | { type: 'SET_METADATA_ENTRIES'; value: KeyValueEntry[] }

const INITIAL_FORM: FormState = {
  name: '',
  description: '',
  capabilities: [],
  metadataEntries: [],
}

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case 'SET_NAME':
      return { ...state, name: action.value }
    case 'SET_DESCRIPTION':
      return { ...state, description: action.value }
    case 'SET_CAPABILITIES':
      return { ...state, capabilities: action.value }
    case 'SET_METADATA_ENTRIES':
      return { ...state, metadataEntries: action.value }
  }
}

// ─── Helpers ────────────────────────────────────────────────────

/** Map 422 validation error items to a field → message record. */
function mapValidationErrors(errors: ValidationErrorItem[]): Record<string, string> {
  const fieldErrors: Record<string, string> = {}
  for (const err of errors) {
    const field = err.loc[err.loc.length - 1]
    if (typeof field === 'string') {
      fieldErrors[field] = err.msg
    }
  }
  return fieldErrors
}

// ─── Component ──────────────────────────────────────────────────

export function CreateAgentPage() {
  const navigate = useNavigate()
  const nameInputRef = useRef<HTMLInputElement>(null)

  // Form state
  const [form, dispatch] = useReducer(formReducer, INITIAL_FORM)

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [generalError, setGeneralError] = useState<string | null>(null)

  // Result (triggers modal)
  const [result, setResult] = useState<AgentCreateResponse | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    // ── Client-side validation
    const trimmedName = form.name.trim()
    if (!trimmedName) {
      setFieldErrors({ name: 'Agent name is required.' })
      nameInputRef.current?.focus()
      return
    }

    // ── Submit
    setIsSubmitting(true)
    setFieldErrors({})
    setGeneralError(null)

    try {
      const metadata = Object.fromEntries(
        form.metadataEntries.filter((e) => e.key.trim()).map((e) => [e.key.trim(), e.value]),
      )

      const response = await createAgent({
        name: trimmedName,
        description: form.description.trim() || undefined,
        capabilities: form.capabilities.length > 0 ? form.capabilities : undefined,
        metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
      })

      setResult(response)
    } catch (err: unknown) {
      if (isApiError(err)) {
        if (err.validationErrors) {
          setFieldErrors(mapValidationErrors(err.validationErrors))
        } else {
          setGeneralError(err.message)
        }
      } else {
        setGeneralError(String(err))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleModalDismiss() {
    if (result) {
      navigate(`/dashboard/agents/${result.agent.id}`)
    }
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-muted">
        <Link to="/dashboard/agents" className="hover:text-ink">
          Agents
        </Link>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4"
        >
          <path
            fillRule="evenodd"
            d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-ink">New Agent</span>
      </nav>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-ink">Create Agent</h1>
        <p className="mt-1 text-sm text-muted">Register a new AI agent identity.</p>
      </div>

      {/* General error */}
      {generalError && (
        <div className="rounded-xl border border-danger bg-danger-soft p-4">
          <p className="text-sm font-medium text-danger" role="alert">
            {generalError}
          </p>
        </div>
      )}

      {/* Form card */}
      <form onSubmit={handleSubmit} className="rounded-xl border border-line bg-surface p-6">
        <div className="space-y-6">
          {/* Name */}
          <div>
            <label htmlFor="agent-name" className="mb-1.5 block text-sm font-medium text-muted">
              Name <span className="text-danger">*</span>
            </label>
            <input
              ref={nameInputRef}
              id="agent-name"
              type="text"
              value={form.name}
              onChange={(e) => dispatch({ type: 'SET_NAME', value: e.target.value })}
              placeholder="My AI Agent"
              autoFocus
              className={`w-full rounded-lg border bg-surface px-3 py-2 text-sm text-ink outline-none transition-colors placeholder:text-faint ${
                fieldErrors.name ? 'border-danger' : 'border-line-strong focus:border-brand'
              }`}
              aria-invalid={!!fieldErrors.name}
              aria-describedby={fieldErrors.name ? 'name-error' : undefined}
            />
            {fieldErrors.name && (
              <p id="name-error" className="mt-1 text-sm text-danger" role="alert">
                {fieldErrors.name}
              </p>
            )}
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="agent-description"
              className="mb-1.5 block text-sm font-medium text-muted"
            >
              Description
            </label>
            <textarea
              id="agent-description"
              value={form.description}
              onChange={(e) => dispatch({ type: 'SET_DESCRIPTION', value: e.target.value })}
              placeholder="A brief description of what this agent does..."
              rows={3}
              className={`w-full resize-none rounded-lg border bg-surface px-3 py-2 text-sm text-ink outline-none transition-colors placeholder:text-faint ${
                fieldErrors.description ? 'border-danger' : 'border-line-strong focus:border-brand'
              }`}
              aria-invalid={!!fieldErrors.description}
              aria-describedby={fieldErrors.description ? 'description-error' : undefined}
            />
            {fieldErrors.description && (
              <p id="description-error" className="mt-1 text-sm text-danger" role="alert">
                {fieldErrors.description}
              </p>
            )}
          </div>

          {/* Capabilities */}
          <div>
            <label
              htmlFor="agent-capabilities"
              className="mb-1.5 block text-sm font-medium text-muted"
            >
              Capabilities
            </label>
            <p className="mb-2 text-xs text-subtle">
              Select capabilities to auto-generate a gateway policy that scopes which endpoints this
              agent can access.
            </p>
            <CapabilitySelect
              id="agent-capabilities"
              selected={form.capabilities}
              onChange={(caps) => dispatch({ type: 'SET_CAPABILITIES', value: caps })}
              error={fieldErrors.capabilities}
            />
          </div>

          {/* Metadata */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-muted">Metadata</label>
            <p className="mb-2 text-xs text-subtle">
              Optional tags for organizing your agents. Use to track team ownership, environment, or
              version.
            </p>
            <KeyValueEditor
              entries={form.metadataEntries}
              onChange={(entries) => dispatch({ type: 'SET_METADATA_ENTRIES', value: entries })}
              error={fieldErrors.metadata}
            />
          </div>
        </div>

        {/* Submit */}
        <div className="mt-8 flex items-center justify-end gap-3 border-t border-line pt-6">
          <Link
            to="/dashboard/agents"
            className="rounded-lg border border-line-strong px-4 py-2 text-sm font-medium text-muted transition-colors hover:bg-elevated"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 rounded-lg bg-brand px-5 py-2 text-sm font-semibold text-brand-ink transition-colors hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-brand"
            aria-busy={isSubmitting}
          >
            {isSubmitting && (
              <svg
                className="h-4 w-4 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            )}
            {isSubmitting ? 'Creating...' : 'Create Agent'}
          </button>
        </div>
      </form>

      {/* Show-once API key modal */}
      {result && (
        <ApiKeyModal
          apiKey={result.api_key}
          agentName={result.agent.name}
          onDismiss={handleModalDismiss}
        />
      )}
    </div>
  )
}
