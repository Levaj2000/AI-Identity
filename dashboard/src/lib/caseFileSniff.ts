/**
 * Lightweight client-side check: does a dropped JSON document look like a Case
 * File *report* (the signed `case-file-*.json`), or did someone drop the wrong
 * file? A real report is a JSON object carrying the audit `events` (or
 * `entries`) array — see `cli/ai_identity_verify.py` (`report`/`chain` read
 * `report_id`/`report_signature`/`events`).
 *
 * The point is UX: dropping an evidence-anchor file (checkpoints.json,
 * inclusion-proofs.json) or a JWKS file onto the server-side Case File verifier
 * used to return "Chain broken / Signature invalid" — which reads like
 * tampering. We catch that here and point the user at the right tool instead,
 * before any upload happens.
 */

export type CaseFileSniff = { ok: true } | { ok: false; hint: string }

const INCLUSION_VERIFIER_HINT = 'Use the “Verify event inclusion” panel below instead.'

export function sniffCaseFile(doc: unknown): CaseFileSniff {
  // checkpoints.json ships as a bare array of {merkle_root, envelope}.
  if (Array.isArray(doc)) {
    return {
      ok: false,
      hint: `This looks like an evidence-anchor file (checkpoints.json), not a Case File report. ${INCLUSION_VERIFIER_HINT}`,
    }
  }
  if (!doc || typeof doc !== 'object') {
    return { ok: false, hint: 'This doesn’t look like a Case File report (.json).' }
  }
  const o = doc as Record<string, unknown>

  // inclusion-proofs.json → {proofs, pending}; jwks.json → {keys}.
  if (Array.isArray(o.proofs)) {
    return {
      ok: false,
      hint: `This looks like an evidence-anchor file (inclusion-proofs.json), not a Case File report. ${INCLUSION_VERIFIER_HINT}`,
    }
  }
  if (Array.isArray(o.keys)) {
    return {
      ok: false,
      hint: `This looks like a JWKS public-key file, not a Case File report. ${INCLUSION_VERIFIER_HINT}`,
    }
  }

  // A real report carries the audit rows under `events` (or legacy `entries`).
  if (Array.isArray(o.events) || Array.isArray(o.entries)) {
    return { ok: true }
  }

  return {
    ok: false,
    hint: 'This doesn’t look like a Case File report (.json) — it has no events. Export one from the Case File page (Export → JSON report or Verification bundle).',
  }
}
