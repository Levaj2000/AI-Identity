import { useEffect, useRef, useState, useSyncExternalStore } from 'react'

interface CountUpOptions {
  /** Target number to count to */
  end: number
  /** Animation duration in ms (default: 2000) */
  duration?: number
  /** Only starts when true (default: true) */
  trigger?: boolean
  /** Suffix appended to display value (e.g. "+", "%") */
  suffix?: string
  /** Prefix prepended to display value (e.g. "$", "<") */
  prefix?: string
  /** Number of decimal places (default: 0) */
  decimals?: number
}

interface CountUpResult {
  /** Current numeric value */
  value: number
  /** Formatted display string with locale formatting + prefix/suffix */
  displayValue: string
}

/** EaseOutExpo easing function */
function easeOutExpo(t: number): number {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t)
}

/** Subscribe to prefers-reduced-motion changes */
function subscribeReducedMotion(callback: () => void) {
  const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
  mq.addEventListener('change', callback)
  return () => mq.removeEventListener('change', callback)
}

function getReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function getReducedMotionServer() {
  return false
}

/**
 * Animated number counter with easeOutExpo easing.
 *
 * - RAF-driven for smooth animation
 * - Locale-formatted output (e.g. "50,000+")
 * - Immediately shows final value on `prefers-reduced-motion`
 */
export function useCountUp({
  end,
  duration = 2000,
  trigger = true,
  suffix = '',
  prefix = '',
  decimals = 0,
}: CountUpOptions): CountUpResult {
  const reducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotion,
    getReducedMotionServer,
  )
  const [value, setValue] = useState(0)
  const rafRef = useRef(0)
  const startTimeRef = useRef(0)

  useEffect(() => {
    if (reducedMotion || !trigger) {
      // Use RAF to set state asynchronously (lint-safe)
      const id = requestAnimationFrame(() => {
        setValue(reducedMotion ? end : 0)
      })
      return () => cancelAnimationFrame(id)
    }

    startTimeRef.current = 0

    const animate = (timestamp: number) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp

      const elapsed = timestamp - startTimeRef.current
      const progress = Math.min(elapsed / duration, 1)
      const eased = easeOutExpo(progress)
      setValue(progress >= 1 ? end : eased * end)

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      }
    }

    rafRef.current = requestAnimationFrame(animate)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [end, duration, trigger, reducedMotion])

  const rounded = decimals > 0 ? Number(value.toFixed(decimals)) : Math.round(value)
  const formatted = rounded.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })

  return {
    value: rounded,
    displayValue: `${prefix}${formatted}${suffix}`,
  }
}
