/**
 * Drag-and-drop Case File verifier.
 *
 * Drop a downloaded Case File .json and the server runs the SAME
 * cli/ai_identity_verify.py a customer runs offline (with the caller's org
 * forensic key) — so verification is one drop, no terminal, no key entry,
 * and the result can't drift from the offline CLI.
 */
import { useCallback, useRef, useState } from 'react'

import { API_BASE_URL } from '../../config/api'
import { getAuthHeaders } from '../../services/api/client'

interface VerifyResult {
  verified: boolean
  chain_intact: boolean
  signature_valid: boolean
  filename?: string
  chain?: { details?: { total_entries?: number; entries_verified?: number; mode?: string } }
}

type State = 'idle' | 'verifying' | 'done' | 'error'

export function CaseFileVerifyPanel() {
  const [state, setState] = useState<State>('idle')
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const verify = useCallback(async (file: File) => {
    setState('verifying')
    setResult(null)
    setErrorMsg('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      // getAuthHeaders returns Authorization / X-API-Key only — no Content-Type,
      // so the browser sets the multipart boundary itself.
      const headers = await getAuthHeaders()
      const resp = await fetch(`${API_BASE_URL}/api/v1/audit/verify`, {
        method: 'POST',
        headers,
        body: fd,
      })
      if (!resp.ok) {
        const e = await resp.json().catch(() => ({}))
        throw new Error(e?.detail || e?.message || `Verification failed (${resp.status})`)
      }
      setResult((await resp.json()) as VerifyResult)
      setState('done')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Verification failed')
      setState('error')
    }
  }, [])

  const onFiles = (files: FileList | null) => {
    const f = files?.[0]
    if (f) verify(f)
  }

  const d = result?.chain?.details

  return (
    <div className="rounded-2xl border border-line bg-surface p-6">
      <h2 className="text-lg font-semibold text-ink">Verify a Case File</h2>
      <p className="mt-1 text-sm text-muted">
        Drop a downloaded Case File (.json) to check its integrity — no terminal, no key to enter.
        Runs the same verifier an outside auditor would.
      </p>

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
          className="hidden"
          onChange={(e) => onFiles(e.target.files)}
        />
        {state === 'verifying' ? (
          <p className="text-sm font-medium text-muted">Verifying…</p>
        ) : (
          <>
            <p className="text-sm font-medium text-ink">Drop a Case File .json here</p>
            <p className="mt-1 text-xs text-muted">
              or click to choose — verified with your org key
            </p>
          </>
        )}
      </div>

      {state === 'done' && result && (
        <div
          className={`mt-4 rounded-xl border p-4 ${
            result.verified ? 'border-success bg-success-soft' : 'border-danger bg-danger-soft'
          }`}
        >
          <div className="flex items-center gap-2">
            <span
              className={`text-2xl font-bold ${result.verified ? 'text-success' : 'text-danger'}`}
            >
              {result.verified ? '✓' : '✗'}
            </span>
            <div>
              <p
                className={`text-lg font-semibold ${
                  result.verified ? 'text-success' : 'text-danger'
                }`}
              >
                {result.verified ? 'VERIFIED' : 'NOT VERIFIED'}
              </p>
              {result.filename && <p className="text-xs text-muted">{result.filename}</p>}
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-1.5">
              <span className={result.chain_intact ? 'text-success' : 'text-danger'}>
                {result.chain_intact ? '✓' : '✗'}
              </span>
              <span className="text-muted">Chain {result.chain_intact ? 'intact' : 'broken'}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={result.signature_valid ? 'text-success' : 'text-danger'}>
                {result.signature_valid ? '✓' : '✗'}
              </span>
              <span className="text-muted">
                Signature {result.signature_valid ? 'valid' : 'invalid'}
              </span>
            </div>
          </div>
          {d?.total_entries != null && (
            <p className="mt-2 text-xs text-subtle">
              {d.entries_verified}/{d.total_entries} entries verified
              {d.mode ? ` · ${d.mode} mode` : ''}
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
