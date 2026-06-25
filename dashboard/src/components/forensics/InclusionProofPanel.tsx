/**
 * Evidence Anchor — in-browser inclusion-proof verifier.
 *
 * Drop the `evidence-anchor/` files from a Case File bundle (checkpoints.json +
 * inclusion-proofs.json) and this proves each event is committed to a signed
 * Merkle checkpoint using ONLY the published ECDSA-P256 public key + SHA-256 —
 * entirely in the browser, no server round-trip for the crypto. This is the
 * public-key verifiability story the HMAC chain can't give (that needs the
 * shared secret); here a third party with zero access to AUDIT_HMAC_KEY can
 * check inclusion. Mirrors `cli/ai_identity_verify.py inclusion-proof`.
 *
 * The only network call is fetching the public JWKS; dropping a pinned JWKS
 * file (the `keys` document) instead makes verification fully offline.
 */
import { useCallback, useRef, useState } from 'react'

import { API_BASE_URL } from '../../config/api'
import {
  classifyAnchorJson,
  verifyInclusion,
  type CheckpointEntry,
  type InclusionProof,
  type Jwks,
  type VerifyReport,
} from '../../lib/evidenceAnchor'

const JWKS_URL = `${API_BASE_URL}/.well-known/ai-identity-public-keys.json`

type State = 'idle' | 'verifying' | 'done' | 'error'

export function InclusionProofPanel() {
  const [state, setState] = useState<State>('idle')
  const [report, setReport] = useState<VerifyReport | null>(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [jwksSource, setJwksSource] = useState<'published' | 'pinned'>('published')
  const inputRef = useRef<HTMLInputElement>(null)

  const run = useCallback(async (files: FileList) => {
    setState('verifying')
    setReport(null)
    setErrorMsg('')
    try {
      // Accumulate across however many evidence-anchor files were dropped, in
      // any order: checkpoints.json (array), inclusion-proofs.json ({proofs}),
      // and optionally a pinned JWKS document ({keys}).
      let checkpoints: CheckpointEntry[] | undefined
      let proofs: InclusionProof[] | undefined
      let pending: number[] = []
      let pinnedJwks: Jwks | undefined

      for (const file of Array.from(files)) {
        let doc: unknown
        try {
          doc = JSON.parse(await file.text())
        } catch {
          throw new Error(`${file.name} is not valid JSON`)
        }
        const parsed = classifyAnchorJson(doc)
        if (parsed.checkpoints) checkpoints = parsed.checkpoints
        if (parsed.proofs) proofs = parsed.proofs
        if (parsed.pending) pending = parsed.pending
        if (parsed.jwks) pinnedJwks = parsed.jwks
      }

      if (!checkpoints || !proofs) {
        throw new Error(
          'Drop both evidence-anchor files: checkpoints.json and inclusion-proofs.json (from a Case File bundle).',
        )
      }

      let jwks: Jwks
      if (pinnedJwks) {
        jwks = pinnedJwks
        setJwksSource('pinned')
      } else {
        setJwksSource('published')
        const resp = await fetch(JWKS_URL, { headers: { Accept: 'application/json' } })
        if (!resp.ok) throw new Error(`Could not fetch published keys (${resp.status})`)
        jwks = (await resp.json()) as Jwks
      }

      setReport(await verifyInclusion(checkpoints, proofs, pending, jwks))
      setState('done')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Verification failed')
      setState('error')
    }
  }, [])

  const onFiles = (files: FileList | null) => {
    if (files && files.length) run(files)
  }

  return (
    <div className="rounded-2xl border border-line bg-surface p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">
            Verify event inclusion (public key only)
          </h2>
          <p className="mt-1 text-sm text-muted">
            Drop the <code className="text-xs">evidence-anchor/</code> files from a Case File bundle
            (<code className="text-xs">checkpoints.json</code> +{' '}
            <code className="text-xs">inclusion-proofs.json</code>). Proves each event is committed
            to a signed checkpoint using only our published public key — no shared secret, verified
            in your browser.
          </p>
        </div>
        <span className="shrink-0 rounded-md border border-line bg-elevated px-2 py-1 text-xs text-muted">
          100% client-side
        </span>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          onFiles(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
        }}
        className={`mt-4 cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          dragOver ? 'border-brand bg-brand-soft' : 'border-line hover:bg-elevated'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".json,application/json"
          multiple
          className="hidden"
          onChange={(e) => onFiles(e.target.files)}
        />
        {state === 'verifying' ? (
          <p className="text-sm font-medium text-muted">Verifying inclusion…</p>
        ) : (
          <>
            <p className="text-sm font-medium text-ink">
              Drop checkpoints.json + inclusion-proofs.json here
            </p>
            <p className="mt-1 text-xs text-muted">
              or click to choose — add a JWKS file to verify fully offline
            </p>
          </>
        )}
      </div>

      {state === 'done' && report && (
        <div
          className={`mt-4 rounded-xl border p-4 ${
            report.ok ? 'border-success bg-success-soft' : 'border-danger bg-danger-soft'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className={`text-2xl font-bold ${report.ok ? 'text-success' : 'text-danger'}`}>
              {report.ok ? '✓' : '✗'}
            </span>
            <div>
              <p className={`text-lg font-semibold ${report.ok ? 'text-success' : 'text-danger'}`}>
                {report.ok ? 'INCLUSION VERIFIED' : 'INCLUSION NOT VERIFIED'}
              </p>
              <p className="text-xs text-muted">
                {report.checkpointsVerified}/{report.checkpointsTotal} checkpoint signature
                {report.checkpointsTotal === 1 ? '' : 's'} valid · keys:{' '}
                {jwksSource === 'pinned' ? 'pinned JWKS (offline)' : 'published JWKS'}
              </p>
            </div>
          </div>

          {report.error ? (
            <p className="mt-3 text-sm text-danger">{report.error}</p>
          ) : (
            <ul className="mt-3 space-y-1.5">
              {report.events.map((ev, i) => (
                <li key={ev.auditId ?? i} className="flex items-start gap-2 text-sm">
                  <span className={ev.verified ? 'text-success' : 'text-danger'}>
                    {ev.verified ? '✓' : '✗'}
                  </span>
                  <span className="text-muted">
                    {ev.verified ? 'VERIFIED' : 'NOT VERIFIED'}
                    {ev.auditId != null && <> · event #{ev.auditId}</>}{' '}
                    <span className="font-mono text-xs text-subtle">
                      (entry {ev.entryHash.slice(0, 12)}…)
                    </span>
                    {!ev.verified && ev.reason && (
                      <span className="text-danger"> — {ev.reason}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {report.pending.length > 0 && (
            <p className="mt-3 text-xs text-subtle">
              Note: {report.pending.length} exported event
              {report.pending.length === 1 ? '' : 's'} not yet anchored to a checkpoint.
            </p>
          )}
        </div>
      )}

      {state === 'error' && (
        <div className="mt-4 rounded-xl border border-danger bg-danger-soft p-3 text-sm text-danger">
          {errorMsg}
        </div>
      )}
    </div>
  )
}
