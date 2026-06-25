/**
 * Evidence Anchor — in-browser inclusion-proof verifier.
 *
 * Mirrors `cli/ai_identity_verify.py` (the offline CLI) byte-for-byte so the
 * dashboard result can't drift from what an outside auditor runs. Proves a
 * single audit event is committed to a signed Merkle checkpoint using ONLY the
 * published ECDSA-P256 public key + SHA-256 — zero access to AUDIT_HMAC_KEY,
 * and zero server round-trip for the crypto (the only network call is fetching
 * the public JWKS, which an offline-pinned JWKS file can replace).
 *
 * Crypto details that must match the Python signer exactly:
 *  - DSSE PAE:  "DSSEv1 <len(type)> <type> <len(payload)> <payload>"
 *  - leaf hash: SHA256(0x00 ‖ entry_hash_bytes)        (RFC 6962 §2.1)
 *  - node hash: SHA256(0x01 ‖ left ‖ right)
 *  - signature: DER ECDSA-P256/SHA-256 → converted to raw r‖s for WebCrypto.
 */

export const CHECKPOINT_PAYLOAD_TYPE = 'application/vnd.ai-identity.anchor-checkpoint+json'
const DSSE_PREAMBLE = 'DSSEv1'

export interface DsseEnvelope {
  payloadType: string
  payload: string // base64 (standard) of the canonical-JSON checkpoint
  signatures: { keyid: string; sig: string }[] // sig: base64 (standard) DER
}

export interface CheckpointEntry {
  merkle_root: string
  envelope: DsseEnvelope
}

export interface InclusionProof {
  audit_id?: number
  entry_hash: string // hex
  index: number
  tree_size: number
  merkle_root: string // hex
  proof: string[] // hex sibling hashes, leaf→root
}

export interface Jwk {
  kty: string
  crv: string
  x: string
  y: string
  kid: string
  [k: string]: unknown
}

export interface Jwks {
  keys: Jwk[]
}

export interface EventVerdict {
  auditId?: number
  entryHash: string
  verified: boolean
  reason?: string
}

export interface VerifyReport {
  ok: boolean
  events: EventVerdict[]
  pending: number[]
  checkpointsVerified: number
  checkpointsTotal: number
  error?: string
}

// ── byte helpers ──────────────────────────────────────────────────────────

function hexToBytes(hex: string): Uint8Array {
  if (hex.length % 2 !== 0) throw new Error('odd-length hex')
  const out = new Uint8Array(hex.length / 2)
  for (let i = 0; i < out.length; i++) {
    const b = Number.parseInt(hex.slice(i * 2, i * 2 + 2), 16)
    if (Number.isNaN(b)) throw new Error('invalid hex')
    out[i] = b
  }
  return out
}

function bytesToHex(bytes: Uint8Array): string {
  let s = ''
  for (const b of bytes) s += b.toString(16).padStart(2, '0')
  return s
}

function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

function concat(...parts: Uint8Array[]): Uint8Array {
  const total = parts.reduce((n, p) => n + p.length, 0)
  const out = new Uint8Array(total)
  let off = 0
  for (const p of parts) {
    out.set(p, off)
    off += p.length
  }
  return out
}

function timingSafeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i]
  return diff === 0
}

async function sha256(data: Uint8Array): Promise<Uint8Array> {
  const digest = await crypto.subtle.digest('SHA-256', data as BufferSource)
  return new Uint8Array(digest)
}

// ── DSSE PAE — must match common.schemas.forensic_attestation.pae ───────────

export function dssePae(payloadType: string, payload: Uint8Array): Uint8Array {
  const enc = new TextEncoder()
  return concat(
    enc.encode(DSSE_PREAMBLE),
    enc.encode(' '),
    enc.encode(String(enc.encode(payloadType).length)),
    enc.encode(' '),
    enc.encode(payloadType),
    enc.encode(' '),
    enc.encode(String(payload.length)),
    enc.encode(' '),
    payload,
  )
}

// ── DER ECDSA signature → raw r‖s (WebCrypto wants P1363, not DER) ───────────

export function derToRawEcdsa(der: Uint8Array, size = 32): Uint8Array {
  // SEQUENCE(0x30) len  INTEGER(0x02) lenR r  INTEGER(0x02) lenS s
  let i = 0
  if (der[i++] !== 0x30) throw new Error('bad DER: expected SEQUENCE')
  // sequence length (may be short or long form; signatures are short here)
  if (der[i] & 0x80) {
    const n = der[i++] & 0x7f
    i += n
  } else {
    i++
  }
  const readInt = (): Uint8Array => {
    if (der[i++] !== 0x02) throw new Error('bad DER: expected INTEGER')
    const len = der[i++]
    let val = der.slice(i, i + len)
    i += len
    // strip leading 0x00 sign padding
    while (val.length > 1 && val[0] === 0x00) val = val.slice(1)
    if (val.length > size) throw new Error('DER integer longer than field size')
    const padded = new Uint8Array(size)
    padded.set(val, size - val.length)
    return padded
  }
  const r = readInt()
  const s = readInt()
  return concat(r, s)
}

// ── RFC 6962 §2.1.1 inclusion-proof check (ported from the CLI) ──────────────

export async function merkleVerifyInclusion(
  leafData: Uint8Array,
  index: number,
  treeSize: number,
  proof: Uint8Array[],
  root: Uint8Array,
): Promise<boolean> {
  if (treeSize <= 0 || index < 0 || index >= treeSize) return false
  let fn = index
  let sn = treeSize - 1
  let r = await sha256(concat(new Uint8Array([0x00]), leafData)) // leaf hash
  for (const p of proof) {
    if (sn === 0) return false
    if (fn & 1 || fn === sn) {
      r = await sha256(concat(new Uint8Array([0x01]), p, r))
      if (!(fn & 1)) {
        do {
          fn >>= 1
          sn >>= 1
        } while (!(fn & 1) && fn !== 0)
      }
    } else {
      r = await sha256(concat(new Uint8Array([0x01]), r, p))
    }
    fn >>= 1
    sn >>= 1
  }
  return sn === 0 && timingSafeEqual(r, root)
}

// ── checkpoint signature (DSSE / ECDSA-P256) ────────────────────────────────

async function importJwk(jwk: Jwk): Promise<CryptoKey> {
  // Pass only the fields WebCrypto needs; the published JWK also carries
  // `kid`, `alg`, `use`, and `ai_identity:*` metadata we don't import.
  return crypto.subtle.importKey(
    'jwk',
    { kty: jwk.kty, crv: jwk.crv, x: jwk.x, y: jwk.y, ext: true },
    { name: 'ECDSA', namedCurve: 'P-256' },
    false,
    ['verify'],
  )
}

export interface CheckpointVerification {
  ok: boolean
  signedRoot?: string
  reason?: string
}

export async function verifyCheckpointSignature(
  envelope: DsseEnvelope,
  jwks: Jwks,
): Promise<CheckpointVerification> {
  if (envelope.payloadType !== CHECKPOINT_PAYLOAD_TYPE) {
    return { ok: false, reason: `unexpected payloadType: ${envelope.payloadType}` }
  }
  const sigs = envelope.signatures ?? []
  if (sigs.length !== 1) {
    return { ok: false, reason: `expected exactly 1 signature, got ${sigs.length}` }
  }
  const kid = sigs[0].keyid
  const jwk = jwks.keys.find((k) => k.kid === kid)
  if (!jwk) {
    return { ok: false, reason: `no published key matches kid ${kid} (fail closed)` }
  }

  let payloadBytes: Uint8Array
  let sigRaw: Uint8Array
  try {
    payloadBytes = base64ToBytes(envelope.payload)
    sigRaw = derToRawEcdsa(base64ToBytes(sigs[0].sig))
  } catch (e) {
    return { ok: false, reason: `malformed envelope: ${(e as Error).message}` }
  }

  const key = await importJwk(jwk)
  const signingInput = dssePae(CHECKPOINT_PAYLOAD_TYPE, payloadBytes)
  const valid = await crypto.subtle.verify(
    { name: 'ECDSA', hash: 'SHA-256' },
    key,
    sigRaw as BufferSource,
    signingInput as BufferSource,
  )
  if (!valid) return { ok: false, reason: 'checkpoint signature verification failed' }

  let signedRoot: string
  try {
    signedRoot = JSON.parse(new TextDecoder().decode(payloadBytes)).merkle_root
  } catch {
    return { ok: false, reason: 'checkpoint payload is not valid JSON' }
  }
  return { ok: true, signedRoot }
}

// ── top-level: verify a set of proofs against signed checkpoints ────────────

export async function verifyInclusion(
  checkpoints: CheckpointEntry[],
  proofs: InclusionProof[],
  pending: number[],
  jwks: Jwks,
): Promise<VerifyReport> {
  if (!Array.isArray(checkpoints) || checkpoints.length === 0 || proofs.length === 0) {
    return {
      ok: false,
      events: [],
      pending,
      checkpointsVerified: 0,
      checkpointsTotal: checkpoints?.length ?? 0,
      error: 'No checkpoints or proofs to verify.',
    }
  }

  // Verify each checkpoint's signature ONCE, binding the signed root to the
  // root the proofs reference — a signature over a different root is useless.
  const verifiedRoots = new Map<string, boolean>()
  let checkpointsVerified = 0
  for (const cp of checkpoints) {
    const res = await verifyCheckpointSignature(cp.envelope, jwks)
    const ok = res.ok && res.signedRoot === cp.merkle_root
    if (ok) checkpointsVerified++
    verifiedRoots.set(cp.merkle_root, ok)
  }

  const events: EventVerdict[] = []
  for (const p of proofs) {
    const sigOk = verifiedRoots.get(p.merkle_root) ?? false
    let verified = false
    let reason: string | undefined
    if (!sigOk) {
      reason = 'checkpoint signature for this root did not verify'
    } else {
      try {
        verified = await merkleVerifyInclusion(
          hexToBytes(p.entry_hash),
          p.index,
          p.tree_size,
          p.proof.map(hexToBytes),
          hexToBytes(p.merkle_root),
        )
        if (!verified) reason = 'event not committed to the signed root'
      } catch (e) {
        reason = `malformed proof: ${(e as Error).message}`
      }
    }
    events.push({ auditId: p.audit_id, entryHash: p.entry_hash, verified, reason })
  }

  return {
    ok: events.every((e) => e.verified),
    events,
    pending,
    checkpointsVerified,
    checkpointsTotal: checkpoints.length,
  }
}

// ── input parsing — accept the evidence-anchor bundle files in any order ────

export interface ParsedAnchorInput {
  checkpoints?: CheckpointEntry[]
  proofs?: InclusionProof[]
  pending?: number[]
  jwks?: Jwks
}

/**
 * Classify one dropped JSON document. The evidence-anchor/ folder ships
 * `checkpoints.json` (an array) and `inclusion-proofs.json` ({proofs, pending});
 * we also accept a combined object and an optional pinned JWKS file (offline).
 */
export function classifyAnchorJson(doc: unknown): ParsedAnchorInput {
  const out: ParsedAnchorInput = {}
  if (Array.isArray(doc)) {
    out.checkpoints = doc as CheckpointEntry[]
    return out
  }
  if (doc && typeof doc === 'object') {
    const o = doc as Record<string, unknown>
    if (Array.isArray(o.checkpoints)) out.checkpoints = o.checkpoints as CheckpointEntry[]
    if (Array.isArray(o.proofs)) out.proofs = o.proofs as InclusionProof[]
    if (Array.isArray(o.pending)) out.pending = o.pending as number[]
    if (Array.isArray(o.keys)) out.jwks = o as unknown as Jwks
  }
  return out
}

export { bytesToHex }
