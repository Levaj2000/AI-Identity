import { describe, expect, it } from 'vitest'

import { sniffCaseFile } from '../caseFileSniff'

describe('sniffCaseFile', () => {
  it('accepts a Case File report with events', () => {
    expect(sniffCaseFile({ report_id: 'r1', report_signature: 'sig', events: [] }).ok).toBe(true)
  })

  it('accepts the legacy entries key', () => {
    expect(sniffCaseFile({ entries: [{ id: 1 }] }).ok).toBe(true)
  })

  it('rejects checkpoints.json (a bare array) and points to the inclusion verifier', () => {
    const r = sniffCaseFile([{ merkle_root: 'abc', envelope: {} }])
    expect(r.ok).toBe(false)
    if (!r.ok) {
      expect(r.hint).toMatch(/checkpoints\.json/)
      expect(r.hint).toMatch(/Verify event inclusion/)
    }
  })

  it('rejects inclusion-proofs.json ({proofs})', () => {
    const r = sniffCaseFile({ proofs: [], pending: [] })
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.hint).toMatch(/inclusion-proofs\.json/)
  })

  it('rejects a JWKS file ({keys})', () => {
    const r = sniffCaseFile({ keys: [{ kid: 'k' }] })
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.hint).toMatch(/JWKS/)
  })

  it('rejects an unrelated object with a generic, non-scary hint', () => {
    const r = sniffCaseFile({ hello: 'world' })
    expect(r.ok).toBe(false)
    if (!r.ok) {
      expect(r.hint).toMatch(/doesn’t look like a Case File report/)
      expect(r.hint).not.toMatch(/Signature invalid|tamper/i)
    }
  })

  it('rejects non-objects', () => {
    expect(sniffCaseFile('nope').ok).toBe(false)
    expect(sniffCaseFile(null).ok).toBe(false)
  })
})
