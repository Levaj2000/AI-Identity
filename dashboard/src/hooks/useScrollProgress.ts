import { useEffect, useRef, useState, useCallback, type RefObject } from 'react'

/**
 * Tracks an element's scroll progress through the viewport.
 * Returns `progress` from 0 (element just entered bottom) to 1 (element exited top).
 *
 * - RAF-throttled, passive scroll listeners
 * - Clamps output to [0, 1]
 */
export function useScrollProgress<T extends HTMLElement = HTMLDivElement>(): {
  ref: RefObject<T | null>
  progress: number
} {
  const ref = useRef<T | null>(null)
  const [progress, setProgress] = useState(0)
  const rafId = useRef(0)

  const calculate = useCallback(() => {
    const el = ref.current
    if (!el) return

    const rect = el.getBoundingClientRect()
    const windowHeight = window.innerHeight

    // 0 when element bottom enters viewport, 1 when element top exits
    const total = windowHeight + rect.height
    const current = windowHeight - rect.top
    const p = Math.max(0, Math.min(1, current / total))

    setProgress(p)
    rafId.current = 0
  }, [])

  useEffect(() => {
    const onScroll = () => {
      if (!rafId.current) {
        rafId.current = requestAnimationFrame(calculate)
      }
    }

    // Initial calculation
    calculate()

    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll, { passive: true })

    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (rafId.current) cancelAnimationFrame(rafId.current)
    }
  }, [calculate])

  return { ref, progress }
}

/**
 * Tracks the global page scroll progress from 0 (top) to 1 (bottom).
 * No ref needed — measures entire document.
 */
export function usePageProgress(): number {
  const [progress, setProgress] = useState(0)
  const rafId = useRef(0)

  useEffect(() => {
    const calculate = () => {
      const scrollTop = window.scrollY
      const docHeight = document.documentElement.scrollHeight - window.innerHeight
      const p = docHeight > 0 ? Math.max(0, Math.min(1, scrollTop / docHeight)) : 0
      setProgress(p)
      rafId.current = 0
    }

    const onScroll = () => {
      if (!rafId.current) {
        rafId.current = requestAnimationFrame(calculate)
      }
    }

    calculate()
    window.addEventListener('scroll', onScroll, { passive: true })

    return () => {
      window.removeEventListener('scroll', onScroll)
      if (rafId.current) cancelAnimationFrame(rafId.current)
    }
  }, [])

  return progress
}
