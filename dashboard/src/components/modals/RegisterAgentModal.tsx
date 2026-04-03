import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { AgentCreateResponse } from '../../types/api'
import { createAgent } from '../../services/api/agents'
import { ApiKeyModal } from './ApiKeyModal'

interface RegisterAgentModalProps {
  shadowAgentId: string
  topEndpoints: Array<{ endpoint: string; method: string; count: number }>
  onComplete: () => void
  onCancel: () => void
}

/**
 * Two-step modal for registering a shadow agent as a real agent.
 *
 * Step 1: Registration form (name, description, endpoint preview)
 * Step 2: Show the API key via ApiKeyModal
 */
export function RegisterAgentModal({
  shadowAgentId,
  topEndpoints,
  onComplete,
  onCancel,
}: RegisterAgentModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState(
    `Registered from shadow agent ${shadowAgentId.slice(0, 8)}...`,
  )
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AgentCreateResponse | null>(null)
  const modalRef = useRef<HTMLDivElement>(null)

  // Focus modal on mount
  useEffect(() => {
    modalRef.current?.focus()
  }, [])

  // Escape key dismisses (when not loading and not showing API key)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && !isLoading && !result) {
        onCancel()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onCancel, isLoading, result])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return

    setIsLoading(true)
    setError(null)
    try {
      const res = await createAgent({
        name: name.trim(),
        description: description.trim() || undefined,
      })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register agent')
    } finally {
      setIsLoading(false)
    }
  }

  // Step 2: Show API key
  if (result) {
    return <ApiKeyModal apiKey={result.api_key} agentName={result.agent.name} onDismiss={onComplete} />
  }

  // Step 1: Registration form
  const modal = (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        aria-hidden="true"
        onClick={isLoading ? undefined : onCancel}
      />

      {/* Modal card */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="register-agent-modal-title"
        tabIndex={-1}
        className="relative z-10 w-full max-w-md rounded-2xl border border-[#A6DAFF]/10 bg-[#10131C]/80 backdrop-blur-xl p-6 shadow-2xl outline-none"
      >
        {/* Header */}
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#A6DAFF]/10">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5 text-[#A6DAFF]"
            >
              <path d="M10 5a3 3 0 11-6 0 3 3 0 016 0zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM16.25 5.75a.75.75 0 00-1.5 0v2h-2a.75.75 0 000 1.5h2v2a.75.75 0 001.5 0v-2h2a.75.75 0 000-1.5h-2v-2z" />
            </svg>
          </div>
          <h2 id="register-agent-modal-title" className="text-lg font-semibold text-[#e4e4e7]">
            Register Shadow Agent
          </h2>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Name */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-[#a1a1aa] mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="e.g. My Research Agent"
              className="w-full rounded-lg border border-[#2a2a2d] bg-[#04070D] px-3 py-2 text-sm text-white placeholder-[#71717a] focus:border-[#A6DAFF]/50 focus:outline-none"
            />
          </div>

          {/* Description */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-[#a1a1aa] mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-[#2a2a2d] bg-[#04070D] px-3 py-2 text-sm text-white placeholder-[#71717a] focus:border-[#A6DAFF]/50 focus:outline-none resize-none"
            />
          </div>

          {/* Endpoints probed */}
          {topEndpoints.length > 0 && (
            <div className="mb-5">
              <label className="block text-xs font-medium text-[#a1a1aa] mb-2">
                Endpoints Probed
              </label>
              <div className="rounded-lg border border-[#2a2a2d] bg-[#04070D] p-3 space-y-1.5 max-h-32 overflow-y-auto">
                {topEndpoints.map((ep) => (
                  <div
                    key={`${ep.method}-${ep.endpoint}`}
                    className="flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-medium text-[#A6DAFF]">{ep.method}</span>
                      <span className="font-mono text-[#d4d4d8]">{ep.endpoint}</span>
                    </div>
                    <span className="text-[#71717a]">{ep.count}x</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Buttons */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className="rounded-lg border border-[#2a2a2d] px-4 py-2 text-sm font-medium text-[#d4d4d8] transition-colors hover:bg-[#1a1a1d] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !name.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-[#A6DAFF] px-4 py-2 text-sm font-semibold text-[#04070D] transition-colors hover:bg-[#A6DAFF]/80 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-[#A6DAFF]"
              aria-busy={isLoading}
            >
              {isLoading && (
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
              Register Agent
            </button>
          </div>
        </form>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
