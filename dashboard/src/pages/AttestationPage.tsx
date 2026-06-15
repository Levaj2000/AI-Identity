import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { isApiError } from '../services/api/client'
import {
  getAttestationBySession,
  getForensicJwks,
  jwksUrl,
  type Attestation,
  type Jwks,
} from '../services/api/attestations'

const RIBBON = ['DSSE envelope', 'ECDSA P-256', 'JWKS (RFC 7517)', 'Offline-verifiable']

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

// ── Trust anchor (public keys) ───────────────────────────────────

function TrustAnchor() {
  const [jwks, setJwks] = useState<Jwks | null | 'error'>(null)

  useEffect(() => {
    let cancelled = false
    getForensicJwks()
      .then((j) => !cancelled && setJwks(j))
      .catch(() => !cancelled && setJwks('error'))
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <div className="mb-1 flex items-start justify-between gap-3">
        <h2 className="text-sm font-medium text-ink">Verification trust anchor</h2>
        <a
          href={jwksUrl()}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-xs text-brand hover:underline"
        >
          Public keys (JWKS) &rarr;
        </a>
      </div>
      <p className="mb-4 text-xs text-subtle">
        Anyone can fetch these public keys and verify a DSSE envelope offline — no dependency on AI
        Identity.
      </p>

      {jwks === null && <div className="h-16 animate-pulse rounded-lg bg-elevated" />}
      {jwks === 'error' && (
        <p className="text-sm text-subtle">Public keys unavailable right now.</p>
      )}
      {jwks && jwks !== 'error' && jwks.keys.length === 0 && (
        <p className="text-sm text-muted">No signing keys published yet (pre-rollout).</p>
      )}
      {jwks && jwks !== 'error' && jwks.keys.length > 0 && (
        <div className="space-y-2">
          {jwks.keys.map((k) => (
            <div
              key={k.kid}
              className="flex items-center justify-between gap-3 rounded-lg border border-line bg-inset px-3 py-2"
            >
              <span className="truncate font-mono text-xs text-ink">{k.kid}</span>
              <span className="shrink-0 text-xs text-subtle">
                {k.kty}
                {k.crv ? ` · ${k.crv}` : ''}
                {k.alg ? ` · ${k.alg}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Look up / verify by session ──────────────────────────────────

type LookupState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'found'; data: Attestation }
  | { status: 'notfound' }
  | { status: 'error'; message: string }

function AttestationLookup() {
  const [sessionId, setSessionId] = useState('')
  const [state, setState] = useState<LookupState>({ status: 'idle' })
  const [showEnvelope, setShowEnvelope] = useState(false)

  async function lookup(e: React.FormEvent) {
    e.preventDefault()
    const id = sessionId.trim()
    if (!id) return
    setState({ status: 'loading' })
    setShowEnvelope(false)
    try {
      const data = await getAttestationBySession(id)
      setState({ status: 'found', data })
    } catch (err) {
      if (isApiError(err) && err.status === 404) {
        setState({ status: 'notfound' })
      } else {
        setState({ status: 'error', message: isApiError(err) ? err.message : 'Lookup failed' })
      }
    }
  }

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <h2 className="text-sm font-medium text-ink">Retrieve &amp; verify an attestation</h2>
      <p className="mb-3 text-xs text-subtle">
        Look up the signed attestation for a session by its ID.
      </p>

      <form onSubmit={lookup} className="flex gap-2">
        <input
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
          placeholder="Session ID (UUID)"
          className="flex-1 rounded-lg border border-line-strong bg-canvas px-3 py-2 font-mono text-sm text-ink placeholder:text-faint focus:border-brand focus:outline-none"
        />
        <button
          type="submit"
          disabled={state.status === 'loading' || !sessionId.trim()}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-ink transition-colors hover:bg-brand-hover disabled:opacity-50"
        >
          {state.status === 'loading' ? 'Looking up…' : 'Look up'}
        </button>
      </form>

      {state.status === 'notfound' && (
        <p className="mt-4 text-sm text-muted">
          No attestation found for that session — it may not exist, or it belongs to another
          organization.
        </p>
      )}
      {state.status === 'error' && <p className="mt-4 text-sm text-danger">{state.message}</p>}

      {state.status === 'found' && (
        <div className="mt-4 space-y-4">
          <div className="flex items-center gap-2 rounded-lg bg-success-soft px-3 py-2 text-sm text-success">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
              <path
                fillRule="evenodd"
                d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                clipRule="evenodd"
              />
            </svg>
            Signed attestation found
          </div>

          <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
            {[
              ['Session', state.data.session_id],
              ['Signed at', formatDate(state.data.signed_at)],
              [
                'Window',
                `${formatDate(state.data.session_start)} → ${formatDate(state.data.session_end)}`,
              ],
              ['Events attested', String(state.data.event_count)],
              ['Audit range', `#${state.data.first_audit_id} – #${state.data.last_audit_id}`],
              ['Signer key', state.data.signer_key_id],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-subtle">{label}</dt>
                <dd className="mt-0.5 break-all font-mono text-xs text-ink">{value}</dd>
              </div>
            ))}
          </dl>

          <div>
            <button
              onClick={() => setShowEnvelope((v) => !v)}
              className="flex items-center gap-1.5 text-sm text-muted hover:text-ink"
            >
              <span>{showEnvelope ? '▾' : '▸'}</span>
              {showEnvelope ? 'Hide' : 'Show'} DSSE envelope
            </button>
            {showEnvelope && (
              <pre className="mt-2 max-h-72 overflow-auto rounded-lg border border-line bg-inset p-3 font-mono text-xs text-muted">
                {JSON.stringify(state.data.envelope, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────

export function AttestationPage() {
  const { user } = useAuth()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Attestation</h1>
        <p className="mt-1 text-sm text-muted">
          DSSE-signed, publicly verifiable session attestations over the tamper-evident audit chain
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {RIBBON.map((s) => (
            <span
              key={s}
              className="rounded-md border border-line bg-surface px-2.5 py-1 text-xs text-muted"
            >
              {s}
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TrustAnchor />
        {user && <AttestationLookup />}
      </div>

      <div className="rounded-xl border border-line bg-surface p-5">
        <h2 className="mb-3 text-sm font-medium text-ink">How verification works</h2>
        <ol className="space-y-2 text-sm text-muted">
          <li>
            <span className="text-ink">1.</span> At session close, AI Identity signs a DSSE envelope
            over the session's audit-chain window with an ECDSA P-256 key.
          </li>
          <li>
            <span className="text-ink">2.</span> The matching public key is published in the JWKS
            above, addressed by <span className="font-mono text-xs">signer_key_id</span>.
          </li>
          <li>
            <span className="text-ink">3.</span> Anyone holding the envelope can verify the
            signature against that public key <span className="text-ink">offline</span> — no API
            call, no trust in AI Identity required.
          </li>
        </ol>
      </div>
    </div>
  )
}
