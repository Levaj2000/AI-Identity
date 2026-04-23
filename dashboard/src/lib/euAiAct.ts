/**
 * EU AI Act Annex III risk-class catalog — dashboard copy of the
 * canonical list maintained on the API side in
 * `common/validation/eu_ai_act.py`. If the Commission publishes
 * corrigenda, update both files together.
 *
 * Used by the Agent edit page to render a dropdown and render the
 * human-readable label on the detail/list views.
 */

export const NOT_IN_SCOPE = 'not_in_scope' as const

/** Ordered for a reasonable dropdown scan — grouped by Annex III category. */
export const ANNEX_III_CATEGORIES: readonly { code: string; label: string }[] = [
  { code: '1(a)', label: 'Biometrics — remote biometric identification' },
  { code: '1(b)', label: 'Biometrics — categorisation by sensitive attributes' },
  { code: '1(c)', label: 'Biometrics — emotion recognition' },
  {
    code: '2(a)',
    label: 'Critical infrastructure — safety components (traffic, utilities, digital)',
  },
  { code: '3(a)', label: 'Education — admission / assignment decisions' },
  { code: '3(b)', label: 'Education — evaluating learning outcomes' },
  { code: '3(c)', label: 'Education — assessing appropriate level of education' },
  { code: '3(d)', label: 'Education — monitoring test behaviour' },
  { code: '4(a)', label: 'Employment — recruitment, job-ad targeting, candidate evaluation' },
  { code: '4(b)', label: 'Employment — promotion/termination, task allocation, monitoring' },
  { code: '5(a)', label: 'Services — public assistance benefits eligibility' },
  { code: '5(b)', label: 'Services — creditworthiness / credit scoring' },
  { code: '5(c)', label: 'Services — emergency dispatch prioritisation' },
  { code: '5(d)', label: 'Services — life / health insurance risk and pricing' },
  { code: '6(a)', label: 'Law enforcement — victim-risk assessment' },
  { code: '6(b)', label: 'Law enforcement — polygraphs and similar' },
  { code: '6(c)', label: 'Law enforcement — evaluating evidence reliability' },
  { code: '6(d)', label: 'Law enforcement — offending / re-offending risk' },
  { code: '6(e)', label: 'Law enforcement — profiling in investigation / prosecution' },
  { code: '7(a)', label: 'Migration / border — polygraphs and similar' },
  { code: '7(b)', label: 'Migration / border — person-risk assessment' },
  { code: '7(c)', label: 'Migration / border — asylum / visa / residence applications' },
  { code: '7(d)', label: 'Migration / border — detection / identification' },
  { code: '8(a)', label: 'Justice — researching and interpreting facts and law' },
  { code: '8(b)', label: 'Democratic processes — influencing elections or voting behaviour' },
] as const

const CODE_TO_LABEL: Record<string, string> = Object.fromEntries(
  ANNEX_III_CATEGORIES.map(({ code, label }) => [code, label]),
)

/**
 * Resolve a stored risk_class value to a human-readable label.
 *
 * - `null` → "Not classified" (with a distinct styling hint for callers).
 * - `"not_in_scope"` → "Not in scope (evaluated out)".
 * - Annex III code → the category description.
 * - Anything else → the raw value, so a not-yet-recognised code still surfaces.
 */
export function riskClassLabel(value: string | null | undefined): string {
  if (value === null || value === undefined) return 'Not classified'
  if (value === NOT_IN_SCOPE) return 'Not in scope (evaluated out)'
  return CODE_TO_LABEL[value] ?? value
}

/** Tri-state classification status for callers that want to style the field. */
export type RiskClassStatus = 'unclassified' | 'out_of_scope' | 'in_scope'

export function riskClassStatus(value: string | null | undefined): RiskClassStatus {
  if (value === null || value === undefined) return 'unclassified'
  if (value === NOT_IN_SCOPE) return 'out_of_scope'
  return 'in_scope'
}
