/**
 * Cross-implementation test: the vector in fixtures/anchor-vector.json is
 * produced by the REAL Python signer (dashboard/scripts/gen_anchor_fixture.py),
 * so these assertions prove the in-browser verifier matches the offline CLI
 * byte-for-byte. If the Python signing/Merkle/PAE encoding ever changes, this
 * test fails until the JS is brought back into lockstep.
 */
import { describe, expect, it } from 'vitest'

import {
  classifyAnchorJson,
  derToRawEcdsa,
  dssePae,
  verifyCheckpointSignature,
  verifyInclusion,
  type CheckpointEntry,
  type InclusionProof,
  type Jwks,
} from '../evidenceAnchor'
import vector from './fixtures/anchor-vector.json'

const checkpoints = vector.checkpoints as unknown as CheckpointEntry[]
const proofs = vector.inclusionProofs.proofs as unknown as InclusionProof[]
const pending = vector.inclusionProofs.pending as number[]
const jwks = vector.jwks as unknown as Jwks

describe('evidenceAnchor — cross-impl vector (Python-signed)', () => {
  it('verifies a real signed checkpoint + inclusion proof', async () => {
    const report = await verifyInclusion(checkpoints, proofs, pending, jwks)
    expect(report.ok).toBe(true)
    expect(report.checkpointsVerified).toBe(1)
    expect(report.events).toHaveLength(1)
    expect(report.events[0].verified).toBe(true)
  })

  it('verifies the checkpoint signature and recovers the signed root', async () => {
    const res = await verifyCheckpointSignature(checkpoints[0].envelope, jwks)
    expect(res.ok).toBe(true)
    expect(res.signedRoot).toBe(checkpoints[0].merkle_root)
  })

  it('fails closed when the kid is not in the JWKS', async () => {
    const emptyJwks: Jwks = { keys: [] }
    const report = await verifyInclusion(checkpoints, proofs, pending, emptyJwks)
    expect(report.ok).toBe(false)
    expect(report.events[0].verified).toBe(false)
    expect(report.events[0].reason).toMatch(/signature/i)
  })

  it('rejects a tampered entry_hash (event not in the signed root)', async () => {
    const tampered = proofs.map((p) => ({
      ...p,
      entry_hash: 'deadbeef'.repeat(8), // 32 bytes, wrong leaf
    }))
    const report = await verifyInclusion(checkpoints, tampered, pending, jwks)
    expect(report.ok).toBe(false)
    expect(report.events[0].reason).toMatch(/not committed/i)
  })

  it('rejects a tampered signature (flip a byte in the DER sig)', async () => {
    const cp = checkpoints[0]
    const sig = cp.envelope.signatures[0].sig
    const bytes = atob(sig).split('')
    bytes[bytes.length - 1] = String.fromCharCode(bytes[bytes.length - 1].charCodeAt(0) ^ 0x01)
    const tamperedCp: CheckpointEntry = {
      ...cp,
      envelope: {
        ...cp.envelope,
        signatures: [{ ...cp.envelope.signatures[0], sig: btoa(bytes.join('')) }],
      },
    }
    const report = await verifyInclusion([tamperedCp], proofs, pending, jwks)
    expect(report.ok).toBe(false)
  })
})

describe('evidenceAnchor — primitives', () => {
  it('dssePae matches the DSSEv1 framing exactly', () => {
    const out = dssePae('text/plain', new TextEncoder().encode('hi'))
    expect(new TextDecoder().decode(out)).toBe('DSSEv1 10 text/plain 2 hi')
  })

  it('derToRawEcdsa pads short integers to 32 bytes (r‖s = 64)', () => {
    // SEQUENCE { INTEGER 0x01, INTEGER 0x02 } → r=0x01 s=0x02, each left-padded
    const der = new Uint8Array([0x30, 0x06, 0x02, 0x01, 0x01, 0x02, 0x01, 0x02])
    const raw = derToRawEcdsa(der)
    expect(raw.length).toBe(64)
    expect(raw[31]).toBe(0x01)
    expect(raw[63]).toBe(0x02)
  })
})

describe('evidenceAnchor — input classification', () => {
  it('classifies a bare array as checkpoints', () => {
    expect(classifyAnchorJson(checkpoints).checkpoints).toHaveLength(1)
  })

  it('classifies {proofs, pending} as inclusion proofs', () => {
    const parsed = classifyAnchorJson(vector.inclusionProofs)
    expect(parsed.proofs).toHaveLength(1)
    expect(parsed.pending).toEqual([])
  })

  it('classifies a JWKS document', () => {
    expect(classifyAnchorJson(jwks).jwks?.keys).toHaveLength(1)
  })
})
