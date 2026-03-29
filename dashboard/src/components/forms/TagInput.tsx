import { useRef, useState } from 'react'

interface TagInputProps {
  tags: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
  id?: string
  error?: string
}

/**
 * Tag input — type text and press Enter to add a pill.
 * Click X on a pill to remove. Backspace on empty input removes last tag.
 * Enter is intercepted to prevent parent form submission.
 */
export function TagInput({
  tags,
  onChange,
  placeholder = 'Type and press Enter',
  id,
  error,
}: TagInputProps) {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  function addTag(value: string) {
    const trimmed = value.trim()
    if (!trimmed) return
    // Deduplicate (case-insensitive)
    if (tags.some((t) => t.toLowerCase() === trimmed.toLowerCase())) return
    onChange([...tags, trimmed])
    setInput('')
  }

  function removeTag(index: number) {
    onChange(tags.filter((_, i) => i !== index))
    inputRef.current?.focus()
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault() // Block form submission
      addTag(input)
    } else if (e.key === 'Backspace' && input === '' && tags.length > 0) {
      removeTag(tags.length - 1)
    }
  }

  const borderColor = error
    ? 'border-red-500 dark:border-red-500'
    : 'border-gray-300 dark:border-[#2a2a2d] focus-within:border-[#A6DAFF] dark:focus-within:border-[#A6DAFF]'

  return (
    <div>
      {/* Container styled as a single input field */}
      <div
        className={`flex min-h-[2.5rem] flex-wrap items-center gap-1.5 rounded-lg border bg-white px-3 py-1.5 transition-colors dark:bg-[#04070D] ${borderColor}`}
        onClick={() => inputRef.current?.focus()}
      >
        {/* Tags */}
        <div role="list" className="contents">
          {tags.map((tag, i) => (
            <span
              key={tag}
              role="listitem"
              className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-gray-100 px-2 py-0.5 font-[JetBrains_Mono,monospace] text-xs text-gray-600 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#a1a1aa]"
            >
              {tag}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  removeTag(i)
                }}
                className="ml-0.5 text-gray-400 transition-colors hover:text-red-500 dark:text-[#71717a] dark:hover:text-red-400"
                aria-label={`Remove ${tag}`}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-3.5 w-3.5"
                >
                  <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                </svg>
              </button>
            </span>
          ))}
        </div>

        {/* Text input */}
        <input
          ref={inputRef}
          id={id}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={tags.length === 0 ? placeholder : ''}
          className="min-w-[120px] flex-1 bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400 dark:text-[#e4e4e7] dark:placeholder:text-[#52525b]"
        />
      </div>

      {/* Error message */}
      {error && (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
