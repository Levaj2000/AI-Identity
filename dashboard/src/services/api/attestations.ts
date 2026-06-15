/**
 * Attestation API — DSSE-signed session attestations + the public JWKS
 * trust anchor used to verify them offline.
 */
import { apiFetch, getApiBaseUrl } from './client'

// ── Types ────────────────────────────────────────────────────────

export interface DSSESignature {
  keyid?: string
  sig: string
}

export interface DSSEEnvelope {
  payload: string
  payloadType: string
  signatures: DSSESignature[]
}

export interface Attestation {
  id: string
  org_id: string
  session_id: string
  first_audit_id: number
  last_audit_id: number
  event_count: number
  session_start: string
  session_end: string
  signed_at: string
  signer_key_id: string
  envelope: DSSEEnvelope
}

export interface Jwk {
  kid: string
  kty: string
  crv?: string
  alg?: string
  use?: string
}

export interface Jwks {
  keys: Jwk[]
}

// ── Calls ────────────────────────────────────────────────────────

/** Fetch the signed attestation for a session (scoped to the caller's orgs). */
export function getAttestationBySession(sessionId: string): Promise<Attestation> {
  return apiFetch<Attestation>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/attestation`)
}

/**
 * Fetch the public JWKS (the verification trust anchor). Public + unauthenticated
 * — anyone can fetch it to verify a DSSE envelope offline.
 */
export async function getForensicJwks(): Promise<Jwks> {
  const res = await fetch(`${getApiBaseUrl()}/.well-known/ai-identity-public-keys.json`)
  if (!res.ok) throw new Error('Failed to load public keys')
  return res.json() as Promise<Jwks>
}

/** The public URL of the JWKS, for display / external verification tools. */
export function jwksUrl(): string {
  return `${getApiBaseUrl()}/.well-known/ai-identity-public-keys.json`
}
