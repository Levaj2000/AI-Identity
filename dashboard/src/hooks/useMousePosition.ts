import { useEffect, useRef, useState, useCallback, type RefObject } from 'react'

interface MousePosition {
  /** Normalized X: -1 (left) to 1 (right) */
  x: number
  /** Normalized Y: -1 (top) to 1 (bottom) */
  y: number
}

/**
 * Tracks cursor position relative to a container element.
 * Returns normalized { x, y } in range [-1, 1].
 *
 * - RAF-throttled for smooth 60fps updates
 * - Resets to {0, 0} on mouseleave
 * - Disabled on touch devices and `prefers-reduced-motion`
 */
export function useMousePosition<T extends HTMLElement = HTMLDivElement>(): {
  ref: RefObject<T | null>
  position: MousePosition
} {
  const ref = useRef<T | null>(null)
  const [position, setPosition] = useState<MousePosition>({ x: 0, y: 0 })
  const rafId = useRef(0)
  const latestPos = useRef<MousePosition>({ x: 0, y: 0 })

  const updatePosition = useCallback(() => {
    setPosition({ ...latestPos.current })
    rafId.current = 0
  }, [])

  useEffect(() => {
    const el = ref.current
    if (!el) return

    // Skip on touch-only devices
    const isTouch = 'ontouchstart' in window && navigator.maxTouchPoints > 0
    if (isTouch) return

    // Skip on reduced-motion preference
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (motionQuery.matches) return

    const handleMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect()
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1
      const y = ((e.clientY - rect.top) / rect.height) * 2 - 1
      latestPos.current = {
        x: Math.max(-1, Math.min(1, x)),
        y: Math.max(-1, Math.min(1, y)),
      }

      if (!rafId.current) {
        rafId.current = requestAnimationFrame(updatePosition)
      }
    }

    const handleLeave = () => {
      latestPos.current = { x: 0, y: 0 }
      if (rafId.current) cancelAnimationFrame(rafId.current)
      rafId.current = 0
      setPosition({ x: 0, y: 0 })
    }

    el.addEventListener('mousemove', handleMove)
    el.addEventListener('mouseleave', handleLeave)

    return () => {
      el.removeEventListener('mousemove', handleMove)
      el.removeEventListener('mouseleave', handleLeave)
      if (rafId.current) cancelAnimationFrame(rafId.current)
    }
  }, [updatePosition])

  return { ref, position }
}
