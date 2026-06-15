import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import type { Organization, OrgMember } from '../types/api'
import {
  getMyOrg,
  createOrg,
  updateOrg,
  deleteOrg,
  listMembers,
  inviteMember,
  updateMemberRole,
  removeMember,
  getForensicVerifyKey,
  regenerateForensicVerifyKey,
  isApiError,
} from '../services/api'
import { ConfirmModal } from '../components/modals/ConfirmModal'

// ─── Helpers ──────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    free: 'bg-elevated text-muted',
    starter: 'bg-brand-soft text-brand',
    pro: 'bg-brand-soft text-brand',
    enterprise: 'bg-brand-soft text-brand',
  }
  const cls = colors[tier.toLowerCase()] || colors.free
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}
    >
      {tier}
    </span>
  )
}

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    owner: 'bg-warning-soft text-warning',
    admin: 'bg-brand-soft text-brand',
    member: 'bg-elevated text-muted',
  }
  const cls = colors[role] || colors.member
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}
    >
      {role}
    </span>
  )
}

// ─── Toast ────────────────────────────────────────────────────────

function Toast({
  message,
  type,
  onDismiss,
}: {
  message: string
  type: 'success' | 'error'
  onDismiss: () => void
}) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000)
    return () => clearTimeout(t)
  }, [onDismiss])

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-fade-in">
      <div
        className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium shadow-lg ${
          type === 'success' ? 'bg-success text-success-ink' : 'bg-danger text-danger-ink'
        }`}
      >
        {type === 'success' ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path
              fillRule="evenodd"
              d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
              clipRule="evenodd"
            />
          </svg>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
              clipRule="evenodd"
            />
          </svg>
        )}
        {message}
        <button onClick={onDismiss} className="ml-2 opacity-70 hover:opacity-100">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      </div>
    </div>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-line bg-surface p-6">
        <div className="h-6 w-48 animate-pulse rounded bg-elevated" />
        <div className="mt-4 h-4 w-64 animate-pulse rounded bg-elevated" />
        <div className="mt-6 flex gap-4">
          <div className="h-16 w-32 animate-pulse rounded-lg bg-elevated" />
          <div className="h-16 w-32 animate-pulse rounded-lg bg-elevated" />
        </div>
      </div>
      <div className="rounded-2xl border border-line bg-surface p-6">
        <div className="h-6 w-36 animate-pulse rounded bg-elevated" />
        <div className="mt-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded bg-elevated" />
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Create Org Card ──────────────────────────────────────────────

function CreateOrgCard({ onCreated }: { onCreated: (org: Organization) => void }) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    setError(null)
    try {
      const org = await createOrg(name.trim())
      onCreated(org)
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create organization')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <div className="rounded-2xl border border-line bg-surface p-8 text-center">
        {/* Icon */}
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-soft">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-7 w-7 text-brand"
          >
            <path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z" />
          </svg>
        </div>

        <h2 className="text-lg font-semibold text-ink">Create Your Organization</h2>
        <p className="mt-2 text-sm text-muted">
          Bring your team together. Create an organization to share agents and manage access.
        </p>

        <form onSubmit={handleCreate} className="mt-6 space-y-4">
          <input
            type="text"
            placeholder="Organization name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink placeholder-faint focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
            required
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <button
            type="submit"
            disabled={loading || !name.trim()}
            className="w-full rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brand-ink transition-colors hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create Organization'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ─── Inline Editable Name ─────────────────────────────────────────

function InlineEditName({
  value,
  onSave,
}: {
  value: string
  onSave: (name: string) => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const [saving, setSaving] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editing])

  async function save() {
    const trimmed = draft.trim()
    if (!trimmed || trimmed === value) {
      setDraft(value)
      setEditing(false)
      return
    }
    setSaving(true)
    try {
      await onSave(trimmed)
      setEditing(false)
    } catch {
      setDraft(value)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') save()
    if (e.key === 'Escape') {
      setDraft(value)
      setEditing(false)
    }
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={save}
        onKeyDown={handleKeyDown}
        disabled={saving}
        className="rounded-lg border border-brand bg-surface px-3 py-1.5 text-xl font-bold text-ink focus:outline-none focus:ring-1 focus:ring-brand"
      />
    )
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className="group flex items-center gap-2 text-xl font-bold text-ink"
      title="Click to edit"
    >
      {value}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="h-4 w-4 text-faint opacity-0 transition-opacity group-hover:opacity-100"
      >
        <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
      </svg>
    </button>
  )
}

// ─── Forensics Key Section ────────────────────────────────────────

const VERIFY_SCRIPT_URL =
  'https://raw.githubusercontent.com/Levaj2000/AI-Identity/main/cli/ai_identity_verify.py'
const VERIFY_SCRIPT_FILENAME = 'ai-identity-verify.py'
const SAMPLE_CHAIN_FILENAME = 'ai-identity-sample-chain.json'

function maskedKey(k: string) {
  // Show an 8-char prefix followed by an ellipsis so a literal copy never
  // pastes fake hex characters (the old `••••` masking did, breaking the CLI).
  return `${k.slice(0, 8)}…`
}

function shellEscapeSingle(value: string): string {
  // POSIX-safe single-quoted string. Embedded apostrophes are escaped as '\''
  return `'${value.replace(/'/g, `'\\''`)}'`
}

function downloadBlob(content: string | Blob, filename: string, mimeType: string) {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// HMAC-SHA256 of `message` (UTF-8) with `keyStr` (UTF-8 bytes — matches the
// Python verifier which does `key.encode("utf-8")` on the hex string).
async function hmacSha256Hex(keyStr: string, message: string): Promise<string> {
  const enc = new TextEncoder()
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    enc.encode(keyStr),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
  const sig = await crypto.subtle.sign('HMAC', cryptoKey, enc.encode(message))
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

// Build the canonical JSON for a sample audit entry.  Field order, separators,
// and value coercion must match `common.audit.writer._canonical_payload`
// (mirrored by `cli/ai_identity_verify.py::_canonical_entry_payload`).
function canonicalEntryPayload(entry: {
  agent_id: string
  cost_estimate_usd: string | null
  created_at: string
  decision: string
  endpoint: string
  latency_ms: number | null
  method: string
  prev_hash: string
}): string {
  return (
    '{' +
    `"agent_id":${JSON.stringify(entry.agent_id)},` +
    `"cost_estimate_usd":${entry.cost_estimate_usd === null ? 'null' : JSON.stringify(entry.cost_estimate_usd)},` +
    `"created_at":${JSON.stringify(entry.created_at)},` +
    `"decision":${JSON.stringify(entry.decision)},` +
    `"endpoint":${JSON.stringify(entry.endpoint)},` +
    `"latency_ms":${entry.latency_ms === null ? 'null' : String(entry.latency_ms)},` +
    `"method":${JSON.stringify(entry.method)},` +
    `"prev_hash":${JSON.stringify(entry.prev_hash)},` +
    `"request_metadata":{"sample":true}` +
    '}'
  )
}

async function buildSampleChainJson(hmacKey: string): Promise<string> {
  const baseAgentId = '00000000-0000-0000-0000-000000000001'
  const entries: Array<Record<string, unknown>> = []

  let prevHash = 'GENESIS'
  const timestamps = ['2026-05-12T10:00:00+00:00', '2026-05-12T10:00:01+00:00']
  const latencies = [42, 38]

  for (let i = 0; i < timestamps.length; i++) {
    const entryBody = {
      agent_id: baseAgentId,
      cost_estimate_usd: null,
      created_at: timestamps[i],
      decision: 'allow',
      endpoint: '/api/v1/sample/echo',
      latency_ms: latencies[i],
      method: 'POST',
      prev_hash: prevHash,
    }
    const canonical = canonicalEntryPayload(entryBody)
    const entryHash = await hmacSha256Hex(hmacKey, canonical)

    entries.push({
      id: i + 1,
      ...entryBody,
      request_metadata: { sample: true },
      entry_hash: entryHash,
    })

    prevHash = entryHash
  }

  return JSON.stringify(entries, null, 2)
}

function ForensicsKeySection({
  onToast,
}: {
  onToast: (message: string, type: 'success' | 'error') => void
}) {
  const [key, setKey] = useState<string | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [noAccess, setNoAccess] = useState(false)
  const [regenerateModal, setRegenerateModal] = useState(false)
  const [regenerateLoading, setRegenerateLoading] = useState(false)
  const [downloadingScript, setDownloadingScript] = useState(false)
  const [downloadingSample, setDownloadingSample] = useState(false)

  useEffect(() => {
    getForensicVerifyKey()
      .then((data) => setKey(data.forensic_verify_key))
      .catch((err) => {
        if (isApiError(err) && (err.status === 403 || err.status === 401)) {
          setNoAccess(true)
        } else {
          onToast('Failed to load forensic verify key', 'error')
        }
      })
      .finally(() => setLoading(false))
  }, [onToast])

  async function handleCopyKey() {
    if (!key) return
    try {
      await navigator.clipboard.writeText(key)
      onToast('Key copied to clipboard', 'success')
    } catch {
      onToast('Failed to copy key', 'error')
    }
  }

  async function handleCopyCommand() {
    if (!key) return
    const command = `AI_IDENTITY_HMAC_KEY=${shellEscapeSingle(key)} python3 ${VERIFY_SCRIPT_FILENAME} chain ./${SAMPLE_CHAIN_FILENAME}`
    try {
      await navigator.clipboard.writeText(command)
      onToast('CLI command copied — paste in a terminal', 'success')
    } catch {
      onToast('Failed to copy command', 'error')
    }
  }

  async function handleDownloadScript() {
    setDownloadingScript(true)
    try {
      const response = await fetch(VERIFY_SCRIPT_URL)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const text = await response.text()
      downloadBlob(text, VERIFY_SCRIPT_FILENAME, 'text/x-python')
      onToast(`Downloaded ${VERIFY_SCRIPT_FILENAME}`, 'success')
    } catch {
      // Fallback: open the raw URL so the user can save it manually.
      window.open(VERIFY_SCRIPT_URL, '_blank')
    } finally {
      setDownloadingScript(false)
    }
  }

  async function handleDownloadSample() {
    if (!key) return
    setDownloadingSample(true)
    try {
      const json = await buildSampleChainJson(key)
      downloadBlob(json, SAMPLE_CHAIN_FILENAME, 'application/json')
      onToast(`Downloaded ${SAMPLE_CHAIN_FILENAME}`, 'success')
    } catch {
      onToast('Failed to build sample chain', 'error')
    } finally {
      setDownloadingSample(false)
    }
  }

  async function handleRegenerate() {
    setRegenerateLoading(true)
    try {
      const data = await regenerateForensicVerifyKey()
      setKey(data.forensic_verify_key)
      setRevealed(false)
      setRegenerateModal(false)
      onToast('Forensic verify key regenerated', 'success')
    } catch (err) {
      onToast(isApiError(err) ? err.message : 'Failed to regenerate key', 'error')
    } finally {
      setRegenerateLoading(false)
    }
  }

  const displayKey = key ? (revealed ? key : maskedKey(key)) : '—'
  const snippetKey = key ? (revealed ? key : maskedKey(key)) : '<your-key>'

  return (
    <div className="rounded-2xl border border-line bg-surface p-6">
      <div className="flex items-center gap-2">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-5 w-5 text-brand"
        >
          <path
            fillRule="evenodd"
            d="M8 7a5 5 0 114.546 4.975L9.5 15H8v1.5H6.5V18H4a1 1 0 01-1-1v-1.879a1 1 0 01.293-.707l4.963-4.963A5.002 5.002 0 018 7zm5-3a.75.75 0 000 1.5A1.5 1.5 0 0114.5 7 .75.75 0 0016 7a3 3 0 00-3-3z"
            clipRule="evenodd"
          />
        </svg>
        <h2 className="text-lg font-semibold text-ink">Forensics</h2>
      </div>
      <p className="mt-1 text-sm text-muted">
        Your organization's HMAC signing key for verifying audit chain exports.
      </p>

      {loading ? (
        <div className="mt-4 h-10 w-full animate-pulse rounded-lg bg-elevated" />
      ) : noAccess ? (
        <div className="mt-4 rounded-lg border border-line bg-inset p-4">
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded-lg border border-line bg-surface px-3 py-2 font-mono text-sm text-faint">
              ••••••••…
            </code>
          </div>
          <p className="mt-3 text-xs text-muted">
            Contact your organization admin or owner to retrieve the audit-log HMAC key for CLI
            verification.
          </p>
        </div>
      ) : (
        <>
          {/* Key display */}
          <div className="mt-4 flex items-center gap-2">
            <code
              data-testid="forensic-key-display"
              className="flex-1 rounded-lg border border-line bg-inset px-3 py-2 font-mono text-sm text-ink"
            >
              {displayKey}
            </code>

            {/* Reveal toggle */}
            <button
              onClick={() => setRevealed((v) => !v)}
              title={revealed ? 'Hide key' : 'Reveal key'}
              aria-label={revealed ? 'Hide key' : 'Reveal key'}
              className="rounded-lg border border-line p-2 text-subtle transition-colors hover:bg-elevated"
            >
              {revealed ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M3.28 2.22a.75.75 0 00-1.06 1.06l14.5 14.5a.75.75 0 101.06-1.06l-1.745-1.745a10.029 10.029 0 003.3-4.38 1.651 1.651 0 000-1.185A10.004 10.004 0 009.999 3a9.956 9.956 0 00-4.744 1.194L3.28 2.22zM7.752 6.69l1.092 1.092a2.5 2.5 0 013.374 3.373l1.091 1.092a4 4 0 00-5.557-5.557z"
                    clipRule="evenodd"
                  />
                  <path d="M10.748 13.93l2.523 2.524a9.987 9.987 0 01-3.27.547c-4.258 0-7.894-2.66-9.337-6.41a1.651 1.651 0 010-1.186A10.007 10.007 0 012.839 6.02L6.07 9.252a4 4 0 004.678 4.678z" />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
                  <path
                    fillRule="evenodd"
                    d="M.664 10.59a1.651 1.651 0 010-1.186A10.004 10.004 0 0110 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0110 17c-4.257 0-7.893-2.66-9.336-6.41z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </button>

            {/* Copy button — always copies the real unmasked key */}
            <button
              onClick={handleCopyKey}
              title="Copy key"
              aria-label="Copy key"
              className="rounded-lg border border-line p-2 text-subtle transition-colors hover:bg-elevated"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
                <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
              </svg>
            </button>

            {/* Regenerate button */}
            <button
              onClick={() => setRegenerateModal(true)}
              className="rounded-lg border border-warning px-3 py-2 text-xs font-medium text-warning transition-colors hover:bg-warning-soft"
            >
              Regenerate
            </button>
          </div>

          {/* CLI usage snippet (manual env-var flow) */}
          <div className="mt-4 rounded-lg border border-line bg-inset p-4">
            <p className="mb-2 text-xs font-medium text-muted">CLI verification (manual)</p>
            <pre className="overflow-x-auto text-xs text-muted">
              {`export AI_IDENTITY_HMAC_KEY='${snippetKey}'
python3 ${VERIFY_SCRIPT_FILENAME} chain export.json`}
            </pre>
          </div>

          {/* CLI Quickstart panel */}
          <div className="mt-4 rounded-lg border border-brand bg-brand-soft p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-ink">Verify CLI — 60 second quickstart</p>
                <p className="mt-0.5 text-xs text-muted">
                  Download the script and a tiny sample chain, then paste one command to see a full
                  round-trip verify.
                </p>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={handleDownloadScript}
                disabled={downloadingScript}
                className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-50"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-3.5 w-3.5"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 3a.75.75 0 01.75.75v8.69l2.22-2.22a.75.75 0 111.06 1.06l-3.5 3.5a.75.75 0 01-1.06 0l-3.5-3.5a.75.75 0 111.06-1.06l2.22 2.22V3.75A.75.75 0 0110 3zM3.75 15.75a.75.75 0 01.75-.75h11a.75.75 0 010 1.5h-11a.75.75 0 01-.75-.75z"
                    clipRule="evenodd"
                  />
                </svg>
                {downloadingScript ? 'Downloading…' : `Download ${VERIFY_SCRIPT_FILENAME}`}
              </button>

              <button
                onClick={handleDownloadSample}
                disabled={downloadingSample || !key}
                className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-50"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-3.5 w-3.5"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 3a.75.75 0 01.75.75v8.69l2.22-2.22a.75.75 0 111.06 1.06l-3.5 3.5a.75.75 0 01-1.06 0l-3.5-3.5a.75.75 0 111.06-1.06l2.22 2.22V3.75A.75.75 0 0110 3zM3.75 15.75a.75.75 0 01.75-.75h11a.75.75 0 010 1.5h-11a.75.75 0 01-.75-.75z"
                    clipRule="evenodd"
                  />
                </svg>
                {downloadingSample ? 'Building…' : `Download sample chain`}
              </button>

              <button
                onClick={handleCopyCommand}
                disabled={!key}
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-brand-ink transition-colors hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-3.5 w-3.5"
                >
                  <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
                  <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
                </svg>
                Copy CLI command
              </button>
            </div>

            <p className="mt-3 text-xs text-muted">
              <span className="font-medium text-ink">VERIFIED ✓</span> means every entry's HMAC and
              chain linkage matches; <span className="font-medium text-ink">TAMPERED ✗</span> means
              an entry was altered or the wrong key was used.
            </p>
            <p className="mt-2 text-xs text-warning">
              <span className="font-semibold">Internal use only.</span> This HMAC key is your
              organization's shared secret — never share it with external auditors or customers. For
              external verification, use the{' '}
              <Link
                to="/dashboard/compliance/exports"
                className="font-medium underline underline-offset-2 hover:text-warning"
              >
                DSSE attestation flow
              </Link>{' '}
              (ECDSA public-key path) instead.
            </p>
          </div>
        </>
      )}

      {/* Regenerate confirmation modal */}
      {regenerateModal && (
        <ConfirmModal
          title="Regenerate Forensic Verify Key"
          message="Regenerating your key does not change existing audit entries, but you will need the old key to verify exports signed before this change."
          confirmLabel="Regenerate Key"
          confirmVariant="danger"
          isLoading={regenerateLoading}
          onConfirm={handleRegenerate}
          onCancel={() => setRegenerateModal(false)}
        />
      )}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────

export function OrganizationPage() {
  const [org, setOrg] = useState<Organization | null>(null)
  const [members, setMembers] = useState<OrgMember[]>([])
  const [loading, setLoading] = useState(true)
  const [noOrg, setNoOrg] = useState(false)

  // Invite form
  const [showInvite, setShowInvite] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<'admin' | 'member'>('member')
  const [inviteLoading, setInviteLoading] = useState(false)
  const [inviteError, setInviteError] = useState<string | null>(null)

  // Modals
  const [deleteModal, setDeleteModal] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [removeMemberModal, setRemoveMemberModal] = useState<OrgMember | null>(null)
  const [removeMemberLoading, setRemoveMemberLoading] = useState(false)

  // Toast
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type })
  }, [])

  // ─── Data Loading ───────────────────────────────────────────────

  const loadData = useCallback(async () => {
    setLoading(true)
    setNoOrg(false)
    try {
      const orgData = await getMyOrg()
      setOrg(orgData)
      const membersData = await listMembers()
      setMembers(membersData)
    } catch (err) {
      if (isApiError(err) && err.status === 404) {
        setNoOrg(true)
      } else {
        showToast(isApiError(err) ? err.message : 'Failed to load organization', 'error')
      }
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => {
    loadData()
  }, [loadData])

  // ─── Actions ────────────────────────────────────────────────────

  async function handleUpdateName(name: string) {
    const updated = await updateOrg(name)
    setOrg(updated)
    showToast('Organization name updated', 'success')
  }

  async function handleDeleteOrg() {
    setDeleteLoading(true)
    try {
      await deleteOrg()
      setOrg(null)
      setMembers([])
      setNoOrg(true)
      setDeleteModal(false)
      showToast('Organization deleted', 'success')
    } catch (err) {
      showToast(isApiError(err) ? err.message : 'Failed to delete organization', 'error')
    } finally {
      setDeleteLoading(false)
    }
  }

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    if (!inviteEmail.trim()) return
    setInviteLoading(true)
    setInviteError(null)
    try {
      const member = await inviteMember(inviteEmail.trim(), inviteRole)
      setMembers((prev) => [...prev, member])
      setInviteEmail('')
      setInviteRole('member')
      setShowInvite(false)
      showToast(`Invited ${member.email}`, 'success')
      // Refresh org to get updated member_count
      try {
        const updated = await getMyOrg()
        setOrg(updated)
      } catch {
        // non-critical
      }
    } catch (err) {
      setInviteError(isApiError(err) ? err.message : 'Failed to invite member')
    } finally {
      setInviteLoading(false)
    }
  }

  async function handleChangeRole(userId: string, role: string) {
    try {
      const updated = await updateMemberRole(userId, role)
      setMembers((prev) => prev.map((m) => (m.user_id === userId ? updated : m)))
      showToast('Role updated', 'success')
    } catch (err) {
      showToast(isApiError(err) ? err.message : 'Failed to update role', 'error')
    }
  }

  async function handleRemoveMember() {
    if (!removeMemberModal) return
    setRemoveMemberLoading(true)
    try {
      await removeMember(removeMemberModal.user_id)
      setMembers((prev) => prev.filter((m) => m.user_id !== removeMemberModal.user_id))
      setRemoveMemberModal(null)
      showToast('Member removed', 'success')
      // Refresh org to get updated member_count
      try {
        const updated = await getMyOrg()
        setOrg(updated)
      } catch {
        // non-critical
      }
    } catch (err) {
      showToast(isApiError(err) ? err.message : 'Failed to remove member', 'error')
    } finally {
      setRemoveMemberLoading(false)
    }
  }

  // ─── Render ─────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-ink">Organization</h1>
        <Skeleton />
      </div>
    )
  }

  if (noOrg) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-ink">Organization</h1>
        <CreateOrgCard
          onCreated={(newOrg) => {
            setOrg(newOrg)
            setNoOrg(false)
            showToast('Organization created!', 'success')
            loadData()
          }}
        />
        {toast && (
          <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-ink">Organization</h1>

      {/* ── Section 1: Org Info ─────────────────────────────────────── */}
      {org && (
        <div className="rounded-2xl border border-line bg-surface p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <InlineEditName value={org.name} onSave={handleUpdateName} />
              <div className="flex items-center gap-3">
                <TierBadge tier={org.tier} />
                <span className="text-xs text-subtle">Created {formatDate(org.created_at)}</span>
              </div>
            </div>
            <button
              onClick={() => setDeleteModal(true)}
              className="rounded-lg border border-danger px-4 py-2 text-sm font-medium text-danger transition-colors hover:bg-danger-soft"
            >
              Delete Organization
            </button>
          </div>

          {/* Stats */}
          <div className="mt-6 flex flex-wrap gap-4">
            <div className="rounded-lg border border-line px-4 py-3">
              <p className="text-xs text-subtle">Members</p>
              <p className="text-2xl font-bold text-ink">{org.member_count}</p>
            </div>
            <div className="rounded-lg border border-line px-4 py-3">
              <p className="text-xs text-subtle">Agents</p>
              <p className="text-2xl font-bold text-ink">{org.agent_count}</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Section 2: Team Members ────────────────────────────────── */}
      <div className="rounded-2xl border border-line bg-surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink">Team Members</h2>
          <button
            onClick={() => setShowInvite(!showInvite)}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brand-ink transition-colors hover:bg-brand-hover"
          >
            {showInvite ? 'Cancel' : 'Invite Member'}
          </button>
        </div>

        {/* Invite Form */}
        {showInvite && (
          <form
            onSubmit={handleInvite}
            className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-line bg-inset p-4"
          >
            <div className="flex-1">
              <label className="mb-1 block text-xs font-medium text-muted">Email</label>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
                className="w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink placeholder-faint focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
                required
              />
            </div>
            <div className="w-32">
              <label className="mb-1 block text-xs font-medium text-muted">Role</label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as 'admin' | 'member')}
                className="w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={inviteLoading || !inviteEmail.trim()}
              className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brand-ink transition-colors hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {inviteLoading ? 'Sending...' : 'Send Invite'}
            </button>
            {inviteError && <p className="w-full text-sm text-danger">{inviteError}</p>}
          </form>
        )}

        {/* Members Table */}
        {members.length === 0 ? (
          <div className="mt-6 text-center">
            <p className="text-sm text-subtle">
              No team members yet. Invite someone to get started.
            </p>
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-line">
                  <th className="pb-3 pr-4 font-medium text-subtle">Email</th>
                  <th className="pb-3 pr-4 font-medium text-subtle">Role</th>
                  <th className="pb-3 pr-4 font-medium text-subtle">Joined</th>
                  <th className="pb-3 font-medium text-subtle">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {members.map((member) => (
                  <tr key={member.user_id}>
                    <td className="py-3 pr-4 text-ink">{member.email}</td>
                    <td className="py-3 pr-4">
                      {member.role === 'owner' ? (
                        <RoleBadge role={member.role} />
                      ) : (
                        <select
                          value={member.role}
                          onChange={(e) => handleChangeRole(member.user_id, e.target.value)}
                          className="rounded-lg border border-line-strong bg-surface px-2 py-1 text-xs font-medium text-ink focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
                        >
                          <option value="admin">Admin</option>
                          <option value="member">Member</option>
                        </select>
                      )}
                    </td>
                    <td className="py-3 pr-4 text-muted">{formatDate(member.joined_at)}</td>
                    <td className="py-3">
                      {member.role === 'owner' ? (
                        <span className="text-xs text-faint">--</span>
                      ) : (
                        <button
                          onClick={() => setRemoveMemberModal(member)}
                          className="rounded-lg px-3 py-1 text-xs font-medium text-danger transition-colors hover:bg-danger-soft"
                        >
                          Remove
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Section 3: Forensics ──────────────────────────────────── */}
      {org && <ForensicsKeySection onToast={showToast} />}

      {/* ── Modals ─────────────────────────────────────────────────── */}
      {deleteModal && (
        <ConfirmModal
          title="Delete Organization"
          message="This will permanently delete your organization, remove all members, and unassign all agents. This action cannot be undone."
          confirmLabel="Delete Organization"
          confirmVariant="danger"
          isLoading={deleteLoading}
          onConfirm={handleDeleteOrg}
          onCancel={() => setDeleteModal(false)}
        />
      )}

      {removeMemberModal && (
        <ConfirmModal
          title="Remove Member"
          message={`Remove ${removeMemberModal.email} from the organization? They will lose access to all shared agents.`}
          confirmLabel="Remove"
          confirmVariant="danger"
          isLoading={removeMemberLoading}
          onConfirm={handleRemoveMember}
          onCancel={() => setRemoveMemberModal(null)}
        />
      )}

      {/* Toast */}
      {toast && (
        <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
      )}
    </div>
  )
}
