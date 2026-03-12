const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 365 * 24 * 60 * 60],
  ['month', 30 * 24 * 60 * 60],
  ['week', 7 * 24 * 60 * 60],
  ['day', 24 * 60 * 60],
  ['hour', 60 * 60],
  ['minute', 60],
  ['second', 1],
]

const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

/** Converts an ISO 8601 timestamp to a human-readable relative string. */
export function relativeTime(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000)

  for (const [unit, threshold] of UNITS) {
    if (Math.abs(seconds) >= threshold) {
      return rtf.format(-Math.round(seconds / threshold), unit)
    }
  }

  return 'just now'
}
