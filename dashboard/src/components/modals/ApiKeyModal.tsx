import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { GATEWAY_URL } from '../../config/api'

interface ApiKeyModalProps {
  apiKey: string
  agentName: string
  onDismiss: () => void
}

/**
 * Show-once modal for a newly created API key.
 *
 * - Rendered via portal so it sits above everything
 * - Undismissable: Escape key blocked, backdrop click ignored
 * - Copy button with "Copied!" feedback (2s)
 * - Checkbox acknowledgment required before dismiss button enables
 */
export function ApiKeyModal({ apiKey, agentName, onDismiss }: ApiKeyModalProps) {
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
      // Fallback: select the key text for manual copy
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
        aria-labelledby="api-key-modal-title"
        tabIndex={-1}
        className="relative z-10 w-full max-w-lg rounded-2xl border border-gray-200 bg-white p-6 shadow-2xl outline-none dark:border-[#A6DAFF]/10 dark:bg-[#10131C]/80 dark:backdrop-blur-xl"
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
                d="M8 7a5 5 0 113.61 4.804l-1.903 1.903A.75.75 0 019.17 14H8v1.17a.75.75 0 01-.22.53l-.5.5a.75.75 0 01-.531.22H5.672a.75.75 0 01-.53-.22l-.5-.5a.75.75 0 01-.22-.53V13.59a.75.75 0 01.22-.53L8.196 9.54A5.003 5.003 0 018 7zm5-3a.75.75 0 000 1.5A1.5 1.5 0 0114.5 7 .75.75 0 0016 7a3 3 0 00-3-3z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div>
            <h2
              id="api-key-modal-title"
              className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]"
            >
              API Key Created
            </h2>
            <p className="text-sm text-gray-500 dark:text-[#a1a1aa]">for {agentName}</p>
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
              This key will only be shown once. Copy it now and store it securely. You will not be
              able to see it again.
            </p>
          </div>
        </div>

        {/* Key display + copy */}
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

        {/* Gateway URL + Quick Start */}
        <div className="mb-5 rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-[#2a2a2d] dark:bg-[#1a1a1d]">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
            Gateway URL
          </p>
          <code className="block break-all font-[JetBrains_Mono,monospace] text-sm text-gray-900 dark:text-[#e4e4e7]">
            {GATEWAY_URL}
          </code>
          <p className="mt-3 text-xs text-gray-500 dark:text-[#a1a1aa]">
            Point your agent&rsquo;s base URL here instead of calling OpenAI directly. Use your API
            key above as the <code className="text-[#A6DAFF]">X-API-Key</code> header.
          </p>
        </div>

        {/* Acknowledge checkbox */}
        <label className="mb-5 flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#A6DAFF] focus:ring-[#A6DAFF] dark:border-[#3a3a3d] dark:bg-[#1a1a1d]"
          />
          <span className="text-sm text-gray-700 dark:text-[#d4d4d8]">
            I have saved this API key in a secure location
          </span>
        </label>

        {/* Dismiss button */}
        <button
          type="button"
          onClick={onDismiss}
          disabled={!acknowledged}
          className="w-full rounded-lg bg-[#A6DAFF] px-4 py-2.5 text-sm font-semibold text-[#04070D] transition-colors hover:bg-[#A6DAFF]/80 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-[#A6DAFF]"
        >
          Continue to Agent
        </button>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
