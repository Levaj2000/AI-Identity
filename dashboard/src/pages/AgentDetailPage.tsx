import { useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAgentDetail } from '../hooks/useAgentDetail'
import { deleteAgent, updateAgent } from '../services/api/agents'
import { isApiError } from '../services/api/client'
import { AgentStatusBadge } from '../components/AgentStatusBadge'
import { TagInput } from '../components/forms/TagInput'
import { KeyValueEditor } from '../components/forms/KeyValueEditor'
import { ConfirmModal } from '../components/modals/ConfirmModal'
import { relativeTime } from '../lib/time'
import type { Agent, AgentUpdate, ValidationErrorItem } from '../types/api'

// ─── Edit form types ────────────────────────────────────────────

interface KeyValueEntry {
  key: string
  value: string
}

interface EditForm {
  name: string
  description: string
  capabilities: string[]
  metadataEntries: KeyValueEntry[]
}

// ─── Helpers ────────────────────────────────────────────────────

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

function buildEditForm(agent: Agent): EditForm {
  return {
    name: agent.name,
    description: agent.description || '',
    capabilities: [...agent.capabilities],
    metadataEntries: Object.entries(agent.metadata).map(([key, value]) => ({
      key,
      value: String(value),
    })),
  }
}

function buildChanges(form: EditForm, agent: Agent): AgentUpdate | null {
  const changes: AgentUpdate = {}
  let hasChanges = false

  if (form.name.trim() !== agent.name) {
    changes.name = form.name.trim()
    hasChanges = true
  }

  const newDesc = form.description.trim() || null
  if (newDesc !== agent.description) {
    changes.description = newDesc
    hasChanges = true
  }

  if (JSON.stringify(form.capabilities) !== JSON.stringify(agent.capabilities)) {
    changes.capabilities = form.capabilities
    hasChanges = true
  }

  const newMetadata = Object.fromEntries(
    form.metadataEntries.filter((e) => e.key.trim()).map((e) => [e.key.trim(), e.value]),
  )
  if (JSON.stringify(newMetadata) !== JSON.stringify(agent.metadata)) {
    changes.metadata = newMetadata
    hasChanges = true
  }

  return hasChanges ? changes : null
}

// ─── Chevron icon (breadcrumb) ──────────────────────────────────

function ChevronIcon() {
  return (
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
  )
}

// ─── Component ──────────────────────────────────────────────────

export function AgentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { agent, isLoading, error, notFound, refetch } = useAgentDetail(id)
  const nameInputRef = useRef<HTMLInputElement>(null)

  // Edit mode
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<EditForm>({
    name: '',
    description: '',
    capabilities: [],
    metadataEntries: [],
  })
  const [isSaving, setIsSaving] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [generalError, setGeneralError] = useState<string | null>(null)

  // Status toggle
  const [isTogglingStatus, setIsTogglingStatus] = useState(false)

  // Revoke
  const [showRevokeModal, setShowRevokeModal] = useState(false)
  const [isRevoking, setIsRevoking] = useState(false)

  const isRevoked = agent?.status === 'revoked'

  // ── Edit mode handlers ──────────────────────────────────────

  function enterEditMode() {
    if (!agent) return
    setEditForm(buildEditForm(agent))
    setFieldErrors({})
    setGeneralError(null)
    setIsEditing(true)
    // Focus name input after render
    setTimeout(() => nameInputRef.current?.focus(), 0)
  }

  function cancelEdit() {
    setIsEditing(false)
    setFieldErrors({})
    setGeneralError(null)
  }

  async function handleSave() {
    if (!agent || !id) return

    // Client-side validation
    if (!editForm.name.trim()) {
      setFieldErrors({ name: 'Agent name is required.' })
      nameInputRef.current?.focus()
      return
    }

    const changes = buildChanges(editForm, agent)
    if (!changes) {
      // No changes — just exit edit mode
      setIsEditing(false)
      return
    }

    setIsSaving(true)
    setFieldErrors({})
    setGeneralError(null)

    try {
      await updateAgent(id, changes)
      refetch()
      setIsEditing(false)
    } catch (err: unknown) {
      if (isApiError(err) && err.validationErrors) {
        setFieldErrors(mapValidationErrors(err.validationErrors))
      } else if (isApiError(err)) {
        setGeneralError(err.message)
      } else {
        setGeneralError(String(err))
      }
    } finally {
      setIsSaving(false)
    }
  }

  // ── Status toggle ───────────────────────────────────────────

  async function toggleStatus() {
    if (!agent || !id || isRevoked) return
    const newStatus = agent.status === 'active' ? 'suspended' : 'active'

    setIsTogglingStatus(true)
    try {
      await updateAgent(id, { status: newStatus })
      refetch()
    } catch (err: unknown) {
      setGeneralError(isApiError(err) ? err.message : String(err))
    } finally {
      setIsTogglingStatus(false)
    }
  }

  // ── Revoke ──────────────────────────────────────────────────

  async function handleRevoke() {
    if (!id) return
    setIsRevoking(true)
    try {
      await deleteAgent(id)
      refetch()
      setShowRevokeModal(false)
    } catch (err: unknown) {
      setGeneralError(isApiError(err) ? err.message : String(err))
      setShowRevokeModal(false)
    } finally {
      setIsRevoking(false)
    }
  }

  // ── Loading state ───────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Breadcrumb skeleton */}
        <div className="flex items-center gap-2">
          <div className="h-4 w-16 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
          <div className="h-4 w-4 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
          <div className="h-4 w-32 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
        </div>
        {/* Header skeleton */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <div className="h-7 w-48 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
            <div className="h-5 w-16 animate-pulse rounded-full bg-gray-200 dark:bg-[#1a1a1d]" />
          </div>
          <div className="mt-2 h-4 w-64 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
          <div className="mt-4 flex gap-3">
            <div className="h-9 w-28 animate-pulse rounded-lg bg-gray-200 dark:bg-[#1a1a1d]" />
            <div className="h-9 w-24 animate-pulse rounded-lg bg-gray-200 dark:bg-[#1a1a1d]" />
          </div>
        </div>
        {/* Details skeleton */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
          <div className="space-y-6">
            <div>
              <div className="mb-2 h-4 w-24 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
              <div className="h-4 w-full animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
            </div>
            <div>
              <div className="mb-2 h-4 w-24 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
              <div className="flex gap-2">
                <div className="h-6 w-16 animate-pulse rounded-md bg-gray-200 dark:bg-[#1a1a1d]" />
                <div className="h-6 w-20 animate-pulse rounded-md bg-gray-200 dark:bg-[#1a1a1d]" />
                <div className="h-6 w-24 animate-pulse rounded-md bg-gray-200 dark:bg-[#1a1a1d]" />
              </div>
            </div>
            <div>
              <div className="mb-2 h-4 w-24 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
              <div className="h-16 w-full animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Not found state ─────────────────────────────────────────

  if (notFound) {
    return (
      <div className="space-y-6">
        <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-[#a1a1aa]">
          <Link to="/dashboard/agents" className="hover:text-gray-700 dark:hover:text-[#e4e4e7]">
            Agents
          </Link>
          <ChevronIcon />
          <span className="text-gray-900 dark:text-[#e4e4e7]">Not Found</span>
        </nav>
        <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-12 text-center dark:border-[#2a2a2d] dark:bg-[#111113]/50">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="mx-auto h-10 w-10 text-gray-400 dark:text-[#52525b]"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z"
              clipRule="evenodd"
            />
          </svg>
          <h2 className="mt-4 text-lg font-semibold text-gray-700 dark:text-[#d4d4d8]">
            Agent Not Found
          </h2>
          <p className="mt-2 text-sm text-gray-500 dark:text-[#71717a]">
            The agent you&apos;re looking for doesn&apos;t exist or has been removed.
          </p>
          <div className="mt-6">
            <Link
              to="/dashboard/agents"
              className="inline-flex items-center gap-2 text-sm font-medium text-[#F59E0B] hover:text-[#F59E0B] dark:text-[#F59E0B] dark:hover:text-[#F59E0B]"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path
                  fillRule="evenodd"
                  d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
                  clipRule="evenodd"
                />
              </svg>
              Back to Agents
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // ── Error state ─────────────────────────────────────────────

  if (error) {
    return (
      <div className="space-y-6">
        <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-[#a1a1aa]">
          <Link to="/dashboard/agents" className="hover:text-gray-700 dark:hover:text-[#e4e4e7]">
            Agents
          </Link>
          <ChevronIcon />
          <span className="text-gray-900 dark:text-[#e4e4e7]">{id}</span>
        </nav>
        <div className="rounded-xl border border-red-300 bg-red-50 p-6 dark:border-red-500/20 dark:bg-red-500/10">
          <h2 className="mb-1 font-semibold text-red-600 dark:text-red-400">
            Unable to Load Agent
          </h2>
          <p className="text-sm text-red-500 dark:text-red-400/80">{error.message}</p>
        </div>
      </div>
    )
  }

  // ── No agent (shouldn't happen but guard) ───────────────────

  if (!agent) return null

  // ── Agent detail ────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-[#a1a1aa]">
        <Link to="/dashboard/agents" className="hover:text-gray-700 dark:hover:text-[#e4e4e7]">
          Agents
        </Link>
        <ChevronIcon />
        <span className="text-gray-900 dark:text-[#e4e4e7]">{agent.name}</span>
      </nav>

      {/* Revoked banner */}
      {isRevoked && (
        <div
          className="rounded-xl border border-red-300 bg-red-50 p-4 dark:border-red-500/20 dark:bg-red-500/10"
          role="alert"
        >
          <div className="flex items-center gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5 shrink-0 text-red-600 dark:text-red-400"
            >
              <path
                fillRule="evenodd"
                d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm font-medium text-red-600 dark:text-red-400">
              This agent has been revoked. All API keys have been deactivated. This action cannot be
              undone.
            </p>
          </div>
        </div>
      )}

      {/* General error (from save/toggle/revoke) */}
      {generalError && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-4 dark:border-red-500/20 dark:bg-red-500/10">
          <p className="text-sm font-medium text-red-600 dark:text-red-400" role="alert">
            {generalError}
          </p>
        </div>
      )}

      {/* Header card */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <h1 className="truncate text-2xl font-bold text-gray-900 dark:text-[#e4e4e7]">
                {agent.name}
              </h1>
              <AgentStatusBadge status={agent.status} />
            </div>
            <p className="mt-1 text-sm text-gray-500 dark:text-[#a1a1aa]">
              Created {relativeTime(agent.created_at)} · Updated {relativeTime(agent.updated_at)}
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {/* Manage Keys */}
          <Link
            to={`/agents/${agent.id}/keys`}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-[#2a2a2d] dark:text-[#d4d4d8] dark:hover:bg-[#1a1a1d]"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-4 w-4"
            >
              <path
                fillRule="evenodd"
                d="M8 7a5 5 0 113.61 4.804l-1.903 1.903A.75.75 0 019.17 14H8v1.17a.75.75 0 01-.22.53l-.5.5a.75.75 0 01-.531.22H5.672a.75.75 0 01-.53-.22l-.5-.5a.75.75 0 01-.22-.53V13.59a.75.75 0 01.22-.53L8.196 9.54A5.003 5.003 0 018 7zm5-3a.75.75 0 000 1.5A1.5 1.5 0 0114.5 7 .75.75 0 0016 7a3 3 0 00-3-3z"
                clipRule="evenodd"
              />
            </svg>
            Manage Keys
          </Link>

          {/* Suspend / Activate toggle */}
          {!isRevoked && (
            <button
              type="button"
              onClick={toggleStatus}
              disabled={isTogglingStatus || isEditing}
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                agent.status === 'active'
                  ? 'border-amber-300 text-amber-700 hover:bg-amber-50 dark:border-amber-500/30 dark:text-amber-400 dark:hover:bg-amber-500/10'
                  : 'border-emerald-300 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500/30 dark:text-emerald-400 dark:hover:bg-emerald-500/10'
              }`}
              aria-busy={isTogglingStatus}
            >
              {isTogglingStatus && (
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
              {agent.status === 'active' ? 'Suspend' : 'Activate'}
            </button>
          )}

          {/* Edit / Save / Cancel */}
          {!isRevoked &&
            (isEditing ? (
              <>
                <button
                  type="button"
                  onClick={cancelEdit}
                  disabled={isSaving}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-[#2a2a2d] dark:text-[#d4d4d8] dark:hover:bg-[#1a1a1d]"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 rounded-lg bg-[#F59E0B] px-3 py-2 text-sm font-semibold text-[#0A0A0B] transition-colors hover:bg-[#F59E0B]/80 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-[#F59E0B]"
                  aria-busy={isSaving}
                >
                  {isSaving && (
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
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={enterEditMode}
                className="inline-flex items-center gap-2 rounded-lg bg-[#F59E0B] px-3 py-2 text-sm font-semibold text-[#0A0A0B] transition-colors hover:bg-[#F59E0B]/80"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
                </svg>
                Edit
              </button>
            ))}

          {/* Revoke */}
          {!isRevoked && !isEditing && (
            <button
              type="button"
              onClick={() => setShowRevokeModal(true)}
              className="rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 dark:border-red-500/30 dark:text-red-400 dark:hover:bg-red-500/10"
            >
              Revoke
            </button>
          )}
        </div>
      </div>

      {/* Details card */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
        <div className="space-y-6">
          {/* Name (edit mode only — view mode shows in header) */}
          {isEditing && (
            <div>
              <label
                htmlFor="edit-name"
                className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-[#d4d4d8]"
              >
                Name <span className="text-red-500">*</span>
              </label>
              <input
                ref={nameInputRef}
                id="edit-name"
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 dark:bg-[#0A0A0B] dark:text-[#e4e4e7] dark:placeholder:text-[#52525b] ${
                  fieldErrors.name
                    ? 'border-red-500 dark:border-red-500'
                    : 'border-gray-300 focus:border-[#F59E0B] dark:border-[#2a2a2d] dark:focus:border-[#F59E0B]'
                }`}
                aria-invalid={!!fieldErrors.name}
                aria-describedby={fieldErrors.name ? 'edit-name-error' : undefined}
              />
              {fieldErrors.name && (
                <p
                  id="edit-name-error"
                  className="mt-1 text-sm text-red-600 dark:text-red-400"
                  role="alert"
                >
                  {fieldErrors.name}
                </p>
              )}
            </div>
          )}

          {/* Description */}
          <div>
            <h3 className="mb-1.5 text-sm font-medium text-gray-700 dark:text-[#d4d4d8]">
              Description
            </h3>
            {isEditing ? (
              <>
                <textarea
                  id="edit-description"
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  placeholder="A brief description of what this agent does..."
                  rows={3}
                  className={`w-full resize-none rounded-lg border bg-white px-3 py-2 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 dark:bg-[#0A0A0B] dark:text-[#e4e4e7] dark:placeholder:text-[#52525b] ${
                    fieldErrors.description
                      ? 'border-red-500 dark:border-red-500'
                      : 'border-gray-300 focus:border-[#F59E0B] dark:border-[#2a2a2d] dark:focus:border-[#F59E0B]'
                  }`}
                />
                {fieldErrors.description && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
                    {fieldErrors.description}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-gray-600 dark:text-[#a1a1aa]">
                {agent.description || (
                  <span className="italic text-gray-400 dark:text-[#52525b]">No description</span>
                )}
              </p>
            )}
          </div>

          {/* Capabilities */}
          <div>
            <h3 className="mb-1.5 text-sm font-medium text-gray-700 dark:text-[#d4d4d8]">
              Capabilities
            </h3>
            {isEditing ? (
              <TagInput
                id="edit-capabilities"
                tags={editForm.capabilities}
                onChange={(caps) => setEditForm({ ...editForm, capabilities: caps })}
                placeholder="Type a capability and press Enter"
                error={fieldErrors.capabilities}
              />
            ) : agent.capabilities.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {agent.capabilities.map((cap) => (
                  <span
                    key={cap}
                    className="rounded-md border border-gray-200 bg-gray-100 px-2 py-0.5 font-[JetBrains_Mono,monospace] text-xs text-gray-600 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#a1a1aa]"
                  >
                    {cap}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm italic text-gray-400 dark:text-[#52525b]">No capabilities</p>
            )}
          </div>

          {/* Metadata */}
          <div>
            <h3 className="mb-1.5 text-sm font-medium text-gray-700 dark:text-[#d4d4d8]">
              Metadata
            </h3>
            {isEditing ? (
              <KeyValueEditor
                entries={editForm.metadataEntries}
                onChange={(entries) => setEditForm({ ...editForm, metadataEntries: entries })}
                error={fieldErrors.metadata}
              />
            ) : Object.keys(agent.metadata).length > 0 ? (
              <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-[#2a2a2d]">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50 dark:border-[#2a2a2d] dark:bg-[#1a1a1d]/50">
                      <th className="px-4 py-2 text-left font-medium text-gray-600 dark:text-[#a1a1aa]">
                        Key
                      </th>
                      <th className="px-4 py-2 text-left font-medium text-gray-600 dark:text-[#a1a1aa]">
                        Value
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(agent.metadata).map(([key, value]) => (
                      <tr
                        key={key}
                        className="border-b border-gray-100 last:border-0 dark:border-[#1a1a1d]"
                      >
                        <td className="px-4 py-2 font-[JetBrains_Mono,monospace] text-xs text-gray-700 dark:text-[#d4d4d8]">
                          {key}
                        </td>
                        <td className="px-4 py-2 font-[JetBrains_Mono,monospace] text-xs text-gray-600 dark:text-[#a1a1aa]">
                          {String(value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm italic text-gray-400 dark:text-[#52525b]">No metadata</p>
            )}
          </div>

          {/* Agent ID (always read-only) */}
          <div>
            <h3 className="mb-1.5 text-sm font-medium text-gray-700 dark:text-[#d4d4d8]">
              Agent ID
            </h3>
            <p className="font-[JetBrains_Mono,monospace] text-sm text-gray-600 dark:text-[#a1a1aa]">
              {agent.id}
            </p>
          </div>
        </div>
      </div>

      {/* Revoke confirmation modal */}
      {showRevokeModal && (
        <ConfirmModal
          title="Revoke Agent"
          message="This action is permanent. The agent and all its API keys will be revoked immediately. This cannot be undone."
          confirmLabel="Revoke Agent"
          confirmVariant="danger"
          isLoading={isRevoking}
          onConfirm={handleRevoke}
          onCancel={() => setShowRevokeModal(false)}
        />
      )}
    </div>
  )
}
