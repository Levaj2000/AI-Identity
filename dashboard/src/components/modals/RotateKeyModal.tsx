import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { formatCountdown } from '../../lib/time'

interface RotateKeyModalProps {
  apiKey: string
  newKeyPrefix: string
  rotatedKeyPrefix: string
  expiresAt: string
  onDismiss: () => void
}

/**
 * Show-once modal for a rotated API key.
 *
 * Displays the new key (with copy) AND grace period info for the old key.
 * Same undismissable pattern as ApiKeyModal — Escape blocked, backdrop click ignored,
 * checkbox acknowledgment required.
 */
export function RotateKeyModal({
  apiKey,
  newKeyPrefix,
  rotatedKeyPrefix,
  expiresAt,
  onDismiss,
}: RotateKeyModalProps) {
  const [copied, setCopied] = useState(false)
  const [acknowledged, setAcknowledged] = useState(false)
  const modalRef = useRef<HTMLDivElement>(null)

  // Focus the modal on mount
  useEffect(() => {
    modalRef.current?.focus()
  }, [])

  // Block Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        e.stopPropagation()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(apiKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback: user can manually select the key text
    }
  }

  const modal = (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />

      {/* Modal card */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="rotate-key-modal-title"
        tabIndex={-1}
        className="relative z-10 w-full max-w-lg rounded-2xl border border-gray-200 bg-white p-6 shadow-2xl outline-none dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl"
      >
        {/* Header */}
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-500/10">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5 text-emerald-600 dark:text-emerald-400"
            >
              <path
                fillRule="evenodd"
                d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H4.598a.75.75 0 00-.75.75v3.634a.75.75 0 001.5 0v-2.033l.312.311a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.06-7.846a.75.75 0 00-1.5 0v2.033l-.312-.31A7 7 0 002.848 8.438a.75.75 0 001.449.39 5.5 5.5 0 019.201-2.466l.312.311H11.38a.75.75 0 000 1.5h3.634a.75.75 0 00.75-.75V3.578z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div>
            <h2
              id="rotate-key-modal-title"
              className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]"
            >
              Key Rotated
            </h2>
            <p className="text-sm text-gray-500 dark:text-[#a1a1aa]">New key: {newKeyPrefix}...</p>
          </div>
        </div>

        {/* Warning */}
        <div className="mb-5 rounded-lg border border-amber-300 bg-amber-50 p-3 dark:border-amber-500/30 dark:bg-amber-500/10">
          <div className="flex gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400"
            >
              <path
                fillRule="evenodd"
                d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-amber-800 dark:text-amber-200">
              This key will only be shown once. Copy it now and store it securely.
            </p>
          </div>
        </div>

        {/* New key display + copy */}
        <div className="mb-5">
          <div className="flex items-start gap-2 rounded-lg bg-gray-100 p-4 dark:bg-[#1a1a1d]">
            <code className="min-w-0 flex-1 break-all font-[JetBrains_Mono,monospace] text-sm text-gray-900 dark:text-[#e4e4e7]">
              {apiKey}
            </code>
            <button
              type="button"
              onClick={handleCopy}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                copied
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
                  : 'bg-white text-gray-700 shadow-sm hover:bg-gray-50 dark:bg-[#2a2a2d] dark:text-[#e4e4e7] dark:hover:bg-[#3a3a3d]'
              }`}
            >
              {copied ? (
                <>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-3.5 w-3.5"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Copied!
                </>
              ) : (
                <>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-3.5 w-3.5"
                  >
                    <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
                    <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
                  </svg>
                  Copy
                </>
              )}
            </button>
          </div>
        </div>

        {/* Grace period info */}
        <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50/50 p-4 dark:border-amber-500/20 dark:bg-amber-500/5">
          <div className="flex items-start gap-3">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                Grace Period Active
              </p>
              <p className="mt-1 text-sm text-amber-700 dark:text-amber-300/80">
                Your previous key (
                <code className="font-[JetBrains_Mono,monospace] text-xs">
                  {rotatedKeyPrefix}...
                </code>
                ) will remain valid during the grace period.
              </p>
              <p className="mt-1.5 text-sm font-medium text-amber-800 dark:text-amber-200">
                {formatCountdown(expiresAt)}
              </p>
              <p className="mt-1 text-xs text-amber-600 dark:text-amber-400/70">
                After this period, the old key will be automatically revoked.
              </p>
            </div>
          </div>
        </div>

        {/* Acknowledge checkbox */}
        <label className="mb-5 flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#F59E0B] focus:ring-[#F59E0B] dark:border-[#3a3a3d] dark:bg-[#1a1a1d]"
          />
          <span className="text-sm text-gray-700 dark:text-[#d4d4d8]">
            I have saved the new API key in a secure location
          </span>
        </label>

        {/* Dismiss button */}
        <button
          type="button"
          onClick={onDismiss}
          disabled={!acknowledged}
          className="w-full rounded-lg bg-[#F59E0B] px-4 py-2.5 text-sm font-semibold text-[#0A0A0B] transition-colors hover:bg-[#F59E0B]/80 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-[#F59E0B]"
        >
          Done
        </button>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
