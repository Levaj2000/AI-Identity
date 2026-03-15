import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAgentKeys } from '../hooks/useAgentKeys'
import { createKey, rotateKey, revokeKey } from '../services/api/keys'
import { isApiError } from '../services/api/client'
import { AgentStatusBadge } from '../components/AgentStatusBadge'
import { KeyTable } from '../components/keys/KeyTable'
import { ApiKeyModal } from '../components/modals/ApiKeyModal'
import { RotateKeyModal } from '../components/modals/RotateKeyModal'
import { ConfirmModal } from '../components/modals/ConfirmModal'
import type { AgentKeyCreateResponse, AgentKeyRotateResponse, KeyStatus } from '../types/api'

// ─── Filter tabs ─────────────────────────────────────────────────

type StatusFilter = KeyStatus | 'all'

const FILTER_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'rotated', label: 'Rotated' },
  { value: 'revoked', label: 'Revoked' },
]

// ─── Chevron icon ────────────────────────────────────────────────

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

// ─── Spinner icon ────────────────────────────────────────────────

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

// ─── Component ───────────────────────────────────────────────────

export function AgentKeysPage() {
  const { id } = useParams<{ id: string }>()
  const { agent, keys, isLoading, error, notFound, refetch } = useAgentKeys(id)

  // Client-side filter
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const filteredKeys = statusFilter === 'all' ? keys : keys.filter((k) => k.status === statusFilter)

  // Action results (trigger modals)
  const [createResult, setCreateResult] = useState<AgentKeyCreateResponse | null>(null)
  const [rotateResult, setRotateResult] = useState<AgentKeyRotateResponse | null>(null)
  const [revokeTarget, setRevokeTarget] = useState<number | null>(null)

  // Loading states
  const [isCreating, setIsCreating] = useState(false)
  const [isRotating, setIsRotating] = useState(false)
  const [isRevoking, setIsRevoking] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const isRevoked = agent?.status === 'revoked'
  const hasActiveKey = keys.some((k) => k.status === 'active')

  // Count keys per status for filter tabs
  const counts: Record<StatusFilter, number> = {
    all: keys.length,
    active: keys.filter((k) => k.status === 'active').length,
    rotated: keys.filter((k) => k.status === 'rotated').length,
    revoked: keys.filter((k) => k.status === 'revoked').length,
  }

  // ── Create key ────────────────────────────────────────────────

  async function handleCreate() {
    if (!id) return
    setIsCreating(true)
    setActionError(null)

    try {
      const result = await createKey(id)
      setCreateResult(result)
    } catch (err: unknown) {
      setActionError(isApiError(err) ? err.message : String(err))
    } finally {
      setIsCreating(false)
    }
  }

  function handleCreateDismiss() {
    setCreateResult(null)
    refetch()
  }

  // ── Rotate key ────────────────────────────────────────────────

  async function handleRotate() {
    if (!id) return
    setIsRotating(true)
    setActionError(null)

    try {
      const result = await rotateKey(id)
      setRotateResult(result)
    } catch (err: unknown) {
      setActionError(isApiError(err) ? err.message : String(err))
    } finally {
      setIsRotating(false)
    }
  }

  function handleRotateDismiss() {
    setRotateResult(null)
    refetch()
  }

  // ── Revoke key ────────────────────────────────────────────────

  async function handleRevokeConfirm() {
    if (!id || revokeTarget === null) return
    setIsRevoking(true)
    setActionError(null)

    try {
      await revokeKey(id, revokeTarget)
      setRevokeTarget(null)
      refetch()
    } catch (err: unknown) {
      setActionError(isApiError(err) ? err.message : String(err))
      setRevokeTarget(null)
    } finally {
      setIsRevoking(false)
    }
  }

  // ── Loading state ─────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Breadcrumb skeleton */}
        <div className="flex items-center gap-2">
          <div className="h-4 w-16 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
          <div className="h-4 w-4 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
          <div className="h-4 w-32 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
          <div className="h-4 w-4 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
          <div className="h-4 w-12 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
        </div>
        {/* Header skeleton */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#00FFC2]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <div className="h-6 w-40 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
            <div className="h-5 w-16 animate-pulse rounded-full bg-gray-200 dark:bg-[#1a1a1d]" />
          </div>
        </div>
        {/* Table skeleton */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#00FFC2]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
          <div className="space-y-4">
            <div className="h-8 w-full animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
            <div className="h-12 w-full animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
            <div className="h-12 w-full animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
          </div>
        </div>
      </div>
    )
  }

  // ── Not found ─────────────────────────────────────────────────

  if (notFound) {
    return (
      <div className="space-y-6">
        <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-[#a1a1aa]">
          <Link to="/agents" className="hover:text-gray-700 dark:hover:text-[#e4e4e7]">
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
              to="/agents"
              className="inline-flex items-center gap-2 text-sm font-medium text-[#00FFC2] hover:text-[#00FFC2] dark:text-[#00FFC2] dark:hover:text-[#00FFC2]"
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

  // ── Error state ───────────────────────────────────────────────

  if (error) {
    return (
      <div className="space-y-6">
        <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-[#a1a1aa]">
          <Link to="/agents" className="hover:text-gray-700 dark:hover:text-[#e4e4e7]">
            Agents
          </Link>
          <ChevronIcon />
          <span className="text-gray-900 dark:text-[#e4e4e7]">{id}</span>
          <ChevronIcon />
          <span className="text-gray-900 dark:text-[#e4e4e7]">Keys</span>
        </nav>
        <div className="rounded-xl border border-red-300 bg-red-50 p-6 dark:border-red-500/20 dark:bg-red-500/10">
          <h2 className="mb-1 font-semibold text-red-600 dark:text-red-400">Unable to Load Keys</h2>
          <p className="text-sm text-red-500 dark:text-red-400/80">{error.message}</p>
        </div>
      </div>
    )
  }

  if (!agent) return null

  // ── Main content ──────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-[#a1a1aa]">
        <Link to="/agents" className="hover:text-gray-700 dark:hover:text-[#e4e4e7]">
          Agents
        </Link>
        <ChevronIcon />
        <Link to={`/agents/${id}`} className="hover:text-gray-700 dark:hover:text-[#e4e4e7]">
          {agent.name}
        </Link>
        <ChevronIcon />
        <span className="text-gray-900 dark:text-[#e4e4e7]">Keys</span>
      </nav>

      {/* Agent mini-header */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-[#00FFC2]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">{agent.name}</h1>
          <AgentStatusBadge status={agent.status} />
          <span className="text-sm text-gray-500 dark:text-[#71717a]">&mdash; API Keys</span>
        </div>
      </div>

      {/* Revoked agent banner */}
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
              This agent has been revoked. Key creation and rotation are disabled.
            </p>
          </div>
        </div>
      )}

      {/* Action error */}
      {actionError && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-4 dark:border-red-500/20 dark:bg-red-500/10">
          <p className="text-sm font-medium text-red-600 dark:text-red-400" role="alert">
            {actionError}
          </p>
        </div>
      )}

      {/* Empty state — no keys at all */}
      {keys.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-12 text-center dark:border-[#2a2a2d] dark:bg-[#111113]/50">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="mx-auto h-10 w-10 text-gray-400 dark:text-[#52525b]"
          >
            <path
              fillRule="evenodd"
              d="M8 7a5 5 0 113.61 4.804l-1.903 1.903A.75.75 0 019.17 14H8v1.17a.75.75 0 01-.22.53l-.5.5a.75.75 0 01-.531.22H5.672a.75.75 0 01-.53-.22l-.5-.5a.75.75 0 01-.22-.53V13.59a.75.75 0 01.22-.53L8.196 9.54A5.003 5.003 0 018 7zm5-3a.75.75 0 000 1.5A1.5 1.5 0 0114.5 7 .75.75 0 0016 7a3 3 0 00-3-3z"
              clipRule="evenodd"
            />
          </svg>
          <h2 className="mt-4 text-lg font-semibold text-gray-700 dark:text-[#d4d4d8]">
            No API Keys Yet
          </h2>
          <p className="mt-2 text-sm text-gray-500 dark:text-[#71717a]">
            Create your first API key to start authenticating this agent.
          </p>
          {!isRevoked && (
            <div className="mt-6">
              <button
                type="button"
                onClick={handleCreate}
                disabled={isCreating}
                className="inline-flex items-center gap-2 rounded-lg bg-[#00FFC2] px-5 py-2 text-sm font-semibold text-[#0A0A0B] transition-colors hover:bg-[#00FFC2]/80 disabled:cursor-not-allowed disabled:opacity-50"
                aria-busy={isCreating}
              >
                {isCreating && <Spinner />}
                {isCreating ? 'Creating...' : 'Create Key'}
              </button>
            </div>
          )}
        </div>
      ) : (
        <>
          {/* Action bar: filter tabs + buttons */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            {/* Filter tabs */}
            <div className="flex gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1 dark:border-[#2a2a2d] dark:bg-[#1a1a1d]/50">
              {FILTER_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setStatusFilter(opt.value)}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    statusFilter === opt.value
                      ? 'bg-white text-gray-900 shadow-sm dark:bg-[#2a2a2d] dark:text-[#e4e4e7]'
                      : 'text-gray-500 hover:text-gray-700 dark:text-[#a1a1aa] dark:hover:text-[#e4e4e7]'
                  }`}
                >
                  {opt.label} ({counts[opt.value]})
                </button>
              ))}
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleRotate}
                disabled={isRotating || isRevoked || !hasActiveKey}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-[#2a2a2d] dark:text-[#d4d4d8] dark:hover:bg-[#1a1a1d]"
                title={
                  isRevoked
                    ? 'Agent is revoked'
                    : !hasActiveKey
                      ? 'No active key to rotate'
                      : 'Rotate the active key'
                }
                aria-busy={isRotating}
              >
                {isRotating && <Spinner />}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H4.598a.75.75 0 00-.75.75v3.634a.75.75 0 001.5 0v-2.033l.312.311a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.06-7.846a.75.75 0 00-1.5 0v2.033l-.312-.31A7 7 0 002.848 8.438a.75.75 0 001.449.39 5.5 5.5 0 019.201-2.466l.312.311H11.38a.75.75 0 000 1.5h3.634a.75.75 0 00.75-.75V3.578z"
                    clipRule="evenodd"
                  />
                </svg>
                Rotate
              </button>
              <button
                type="button"
                onClick={handleCreate}
                disabled={isCreating || isRevoked}
                className="inline-flex items-center gap-2 rounded-lg bg-[#00FFC2] px-4 py-2 text-sm font-semibold text-[#0A0A0B] transition-colors hover:bg-[#00FFC2]/80 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-[#00FFC2]"
                title={isRevoked ? 'Agent is revoked' : 'Create a new API key'}
                aria-busy={isCreating}
              >
                {isCreating && <Spinner />}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
                </svg>
                Create Key
              </button>
            </div>
          </div>

          {/* Key table */}
          <KeyTable
            keys={filteredKeys}
            isAgentRevoked={!!isRevoked}
            onRevoke={(keyId) => setRevokeTarget(keyId)}
          />
        </>
      )}

      {/* ── Modals ─────────────────────────────────────────────── */}

      {/* Create key result modal */}
      {createResult && (
        <ApiKeyModal
          apiKey={createResult.api_key}
          agentName={agent.name}
          onDismiss={handleCreateDismiss}
        />
      )}

      {/* Rotate key result modal */}
      {rotateResult && (
        <RotateKeyModal
          apiKey={rotateResult.api_key}
          newKeyPrefix={rotateResult.new_key.key_prefix}
          rotatedKeyPrefix={rotateResult.rotated_key.key_prefix}
          expiresAt={rotateResult.rotated_key.expires_at || ''}
          onDismiss={handleRotateDismiss}
        />
      )}

      {/* Revoke confirmation modal */}
      {revokeTarget !== null && (
        <ConfirmModal
          title="Revoke API Key"
          message="This action is permanent. The API key will be immediately revoked and can no longer be used for authentication."
          confirmLabel="Revoke Key"
          confirmVariant="danger"
          isLoading={isRevoking}
          onConfirm={handleRevokeConfirm}
          onCancel={() => setRevokeTarget(null)}
        />
      )}
    </div>
  )
}
