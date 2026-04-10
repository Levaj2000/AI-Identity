import { useEffect, useRef, useState } from 'react'
import { listCapabilities } from '../../services/api/capabilities'
import { useAuth } from '../../hooks/useAuth'
import type { CapabilityDefinition } from '../../types/api'

interface CapabilitySelectProps {
  /** Currently selected capability IDs */
  selected: string[]
  /** Called when selection changes */
  onChange: (selected: string[]) => void
  /** Field error message */
  error?: string
  /** HTML id for label association */
  id?: string
}

export function CapabilitySelect({ selected, onChange, error, id }: CapabilitySelectProps) {
  const { user } = useAuth()
  const [capabilities, setCapabilities] = useState<CapabilityDefinition[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Fetch capabilities from API
  useEffect(() => {
    if (!user) return
    let cancelled = false
    listCapabilities()
      .then((data) => {
        if (!cancelled) setCapabilities(data)
      })
      .catch(() => {
        // Silently fail — dropdown will be empty
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [user])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function toggleCapability(capId: string) {
    if (selected.includes(capId)) {
      onChange(selected.filter((id) => id !== capId))
    } else {
      onChange([...selected, capId])
    }
  }

  function removeCapability(capId: string) {
    onChange(selected.filter((id) => id !== capId))
  }

  /** Look up display name for a capability ID */
  function getCapName(capId: string): string {
    return capabilities.find((c) => c.id === capId)?.name ?? capId
  }

  const borderColor = error
    ? 'border-red-500 dark:border-red-500'
    : isOpen
      ? 'border-[#A6DAFF] ring-2 ring-[#A6DAFF]/50 dark:border-[#A6DAFF]'
      : 'border-gray-300 dark:border-[#2a2a2d]'

  return (
    <div ref={dropdownRef} className="relative" id={id}>
      {/* Trigger area */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex min-h-[2.5rem] w-full flex-wrap items-center gap-1.5 rounded-lg border bg-white px-3 py-1.5 text-left transition-colors dark:bg-[#04070D] ${borderColor}`}
      >
        {/* Selected pills */}
        {selected.length > 0 ? (
          selected.map((capId) => (
            <span
              key={capId}
              className="inline-flex items-center gap-1 rounded-md border border-[#A6DAFF]/30 bg-[#A6DAFF]/10 px-2 py-0.5 text-xs font-medium text-[#A6DAFF] dark:border-[#A6DAFF]/20 dark:bg-[#A6DAFF]/5"
            >
              {getCapName(capId)}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  removeCapability(capId)
                }}
                className="ml-0.5 rounded-full p-0.5 hover:bg-[#A6DAFF]/20"
                aria-label={`Remove ${getCapName(capId)}`}
              >
                <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                </svg>
              </button>
            </span>
          ))
        ) : (
          <span className="text-sm text-gray-400 dark:text-[#52525b]">
            {isLoading ? 'Loading capabilities...' : 'Select capabilities'}
          </span>
        )}

        {/* Chevron */}
        <svg
          className={`ml-auto h-4 w-4 shrink-0 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg dark:border-[#2a2a2d] dark:bg-[#10131C]">
          {capabilities.length === 0 ? (
            <div className="px-4 py-3 text-sm text-gray-400 dark:text-[#52525b]">
              {isLoading ? 'Loading...' : 'No capabilities available'}
            </div>
          ) : (
            <ul className="max-h-72 overflow-auto py-1" role="listbox" aria-multiselectable="true">
              {capabilities.map((cap) => {
                const isSelected = selected.includes(cap.id)
                return (
                  <li
                    key={cap.id}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => toggleCapability(cap.id)}
                    className="flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-gray-50 dark:hover:bg-[#1a1a1d]"
                  >
                    {/* Checkbox */}
                    <div
                      className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
                        isSelected
                          ? 'border-[#A6DAFF] bg-[#A6DAFF]'
                          : 'border-gray-300 dark:border-[#3a3a3d]'
                      }`}
                    >
                      {isSelected && (
                        <svg
                          className="h-3 w-3 text-[#04070D]"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                    </div>

                    {/* Label + description */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-[#e4e4e7]">
                          {cap.name}
                        </span>
                        <code className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-[#1a1a1d] dark:text-[#71717a]">
                          {cap.id}
                        </code>
                      </div>
                      <p className="mt-0.5 text-xs text-gray-500 dark:text-[#71717a]">
                        {cap.description}
                      </p>
                      <p className="mt-1 font-[JetBrains_Mono,monospace] text-[10px] text-gray-400 dark:text-[#52525b]">
                        {cap.methods.join(', ')} {cap.endpoints.join(', ')}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}

      {/* Error message */}
      {error && (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
