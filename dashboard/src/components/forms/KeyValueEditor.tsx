interface KeyValueEntry {
  key: string
  value: string
}

interface KeyValueEditorProps {
  entries: KeyValueEntry[]
  onChange: (entries: KeyValueEntry[]) => void
  error?: string
}

/**
 * Dynamic key-value pair editor.
 *
 * Starts empty — click "Add metadata" to add rows.
 * Each row has Key + Value inputs and a remove button.
 */
export function KeyValueEditor({ entries, onChange, error }: KeyValueEditorProps) {
  function addRow() {
    onChange([...entries, { key: '', value: '' }])
  }

  function updateRow(index: number, field: 'key' | 'value', newValue: string) {
    onChange(entries.map((entry, i) => (i === index ? { ...entry, [field]: newValue } : entry)))
  }

  function removeRow(index: number) {
    onChange(entries.filter((_, i) => i !== index))
  }

  return (
    <div>
      {/* Rows */}
      {entries.length > 0 && (
        <div className="space-y-2">
          {entries.map((entry, i) => (
            <div key={i} className="flex items-center gap-3">
              <input
                type="text"
                value={entry.key}
                onChange={(e) => updateRow(i, 'key', e.target.value)}
                placeholder="Key"
                className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-600 dark:focus:border-indigo-500"
              />
              <input
                type="text"
                value={entry.value}
                onChange={(e) => updateRow(i, 'value', e.target.value)}
                placeholder="Value"
                className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-600 dark:focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={() => removeRow(i)}
                className="shrink-0 rounded-lg p-2 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-500 dark:text-slate-500 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                aria-label={`Remove metadata row ${i + 1}`}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add button */}
      <button
        type="button"
        onClick={addRow}
        className={`inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 transition-colors hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300 ${entries.length > 0 ? 'mt-3' : ''}`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4"
        >
          <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
        </svg>
        Add metadata
      </button>

      {/* Error message */}
      {error && (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
