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

  const borderColor = error ? 'border-danger' : 'border-line-strong focus-within:border-brand'

  return (
    <div>
      {/* Container styled as a single input field */}
      <div
        className={`flex min-h-[2.5rem] flex-wrap items-center gap-1.5 rounded-lg border bg-canvas px-3 py-1.5 transition-colors ${borderColor}`}
        onClick={() => inputRef.current?.focus()}
      >
        {/* Tags */}
        <div role="list" className="contents">
          {tags.map((tag, i) => (
            <span
              key={tag}
              role="listitem"
              className="inline-flex items-center gap-1 rounded-md border border-line bg-elevated px-2 py-0.5 font-[JetBrains_Mono,monospace] text-xs text-muted"
            >
              {tag}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  removeTag(i)
                }}
                className="ml-0.5 text-subtle transition-colors hover:text-danger"
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
          className="min-w-[120px] flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-faint"
        />
      </div>

      {/* Error message */}
      {error && (
        <p className="mt-1 text-sm text-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
