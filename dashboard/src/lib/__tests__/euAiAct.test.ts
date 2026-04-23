import { describe, expect, it } from 'vitest'
import { ANNEX_III_CATEGORIES, NOT_IN_SCOPE, riskClassLabel, riskClassStatus } from '../euAiAct'

describe('riskClassLabel', () => {
  it('returns "Not classified" for null', () => {
    expect(riskClassLabel(null)).toBe('Not classified')
  })

  it('returns "Not classified" for undefined', () => {
    expect(riskClassLabel(undefined)).toBe('Not classified')
  })

  it('returns an out-of-scope phrasing for the sentinel', () => {
    // Matches "Not in scope (evaluated out)" — the key word for the
    // test's intent is "scope" (vs the silent "unclassified" default).
    expect(riskClassLabel(NOT_IN_SCOPE)).toMatch(/scope/i)
    expect(riskClassLabel(NOT_IN_SCOPE)).not.toBe('Not classified')
  })

  it('resolves known Annex III codes to human-readable labels', () => {
    // 4(a) is HR recruitment — matches the API-side canonical list.
    expect(riskClassLabel('4(a)')).toMatch(/recruitment|employment/i)
  })

  it('falls back to the raw value for unknown codes', () => {
    // If the Commission publishes a new letter before the dashboard
    // catalog is updated, the code should still surface rather than
    // silently blanking out.
    expect(riskClassLabel('9(z)')).toBe('9(z)')
  })
})

describe('riskClassStatus', () => {
  it('null is unclassified', () => {
    expect(riskClassStatus(null)).toBe('unclassified')
  })

  it('undefined is unclassified', () => {
    expect(riskClassStatus(undefined)).toBe('unclassified')
  })

  it('not_in_scope is out_of_scope', () => {
    expect(riskClassStatus(NOT_IN_SCOPE)).toBe('out_of_scope')
  })

  it('an Annex III code is in_scope', () => {
    expect(riskClassStatus('3(a)')).toBe('in_scope')
  })
})

describe('ANNEX_III_CATEGORIES', () => {
  it('has entries for the flagship categories referenced in the scoping doc', () => {
    const codes = new Set(ANNEX_III_CATEGORIES.map((c) => c.code))
    // Sampling one code from each of the eight Annex III buckets — if
    // the catalog drifts, at least one of these drops out.
    for (const expected of ['1(a)', '2(a)', '3(a)', '4(b)', '5(b)', '6(d)', '7(c)', '8(b)']) {
      expect(codes).toContain(expected)
    }
  })

  it('every entry has a non-empty label', () => {
    for (const { code, label } of ANNEX_III_CATEGORIES) {
      expect(label, `label missing for ${code}`).toBeTruthy()
    }
  })
})
