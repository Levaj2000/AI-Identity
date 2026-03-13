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

/**
 * Formats a future expiry timestamp as a human-readable countdown.
 *
 * Returns strings like "23h 14m remaining", "45m remaining", "< 1m remaining",
 * or "Expired" if the time has passed.
 */
export function formatCountdown(expiresAt: string): string {
  const ms = new Date(expiresAt).getTime() - Date.now()

  if (ms <= 0) return 'Expired'

  const hours = Math.floor(ms / 3_600_000)
  const minutes = Math.floor((ms % 3_600_000) / 60_000)

  if (hours > 0) return `${hours}h ${minutes}m remaining`
  if (minutes > 0) return `${minutes}m remaining`
  return '< 1m remaining'
}

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
