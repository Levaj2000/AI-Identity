import { Link } from 'react-router-dom'

/**
 * Standards & frameworks — informational. Lists the standards the platform
 * engages (real product scope), not a per-org compliance claim. Links to the
 * Compliance surface where evidence exports live.
 */
const FRAMEWORKS: { name: string; desc: string }[] = [
  { name: 'OCSF', desc: 'Open Cybersecurity Schema' },
  { name: 'SOC 2', desc: 'Trust services criteria' },
  { name: 'EU AI Act', desc: 'AI risk classification' },
  { name: 'NIST AI RMF', desc: 'AI risk management' },
]

export function StandardsPanel() {
  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-medium text-ink">Standards &amp; frameworks</h2>
        <Link to="/dashboard/compliance" className="text-xs text-brand hover:underline">
          View &rarr;
        </Link>
      </div>
      <p className="mb-3 text-xs text-subtle">Standards this platform aligns to</p>
      <div className="space-y-2.5">
        {FRAMEWORKS.map((f) => (
          <div
            key={f.name}
            className="flex items-center justify-between border-t border-line pt-2.5 first:border-t-0 first:pt-0"
          >
            <span className="text-sm text-ink">{f.name}</span>
            <span className="text-xs text-subtle">{f.desc}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
