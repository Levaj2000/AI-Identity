import { useEffect, useRef, useState, useSyncExternalStore } from 'react'

interface TypewriterOptions {
  /** The full string to type out */
  text: string
  /** Milliseconds per character (default: 55) */
  speed?: number
  /** Delay before typing starts in ms (default: 0) */
  startDelay?: number
  /** Only starts typing when true (default: true) */
  trigger?: boolean
}

interface TypewriterResult {
  /** The currently visible portion of the text */
  displayText: string
  /** Whether typing has completed */
  isComplete: boolean
  /** Whether the blinking cursor should be visible */
  cursorVisible: boolean
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
 * Character-by-character typewriter animation.
 *
 * - Blinking cursor (530ms toggle) during and after typing
 * - Immediately shows full text on `prefers-reduced-motion`
 */
export function useTypewriter({
  text,
  speed = 55,
  startDelay = 0,
  trigger = true,
}: TypewriterOptions): TypewriterResult {
  // Track text changes via a version key — when text changes,
  // increment version to reset all animation state through deps
  const [textVersion, setTextVersion] = useState(0)
  const prevTextRef = useRef(text)
  const [charIndex, setCharIndex] = useState(0)
  const [started, setStarted] = useState(false)
  const [cursorVisible, setCursorVisible] = useState(true)
  const reducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotion,
    getReducedMotionServer,
  )
  const intervalRef = useRef<ReturnType<typeof setInterval>>(null)
  const cursorRef = useRef<ReturnType<typeof setInterval>>(null)

  // Reset when text prop changes — ref access in effects is lint-safe,
  // and setState calls are wrapped in RAF to be asynchronous
  useEffect(() => {
    if (prevTextRef.current === text) return
    prevTextRef.current = text

    const id = requestAnimationFrame(() => {
      setCharIndex(0)
      setStarted(false)
      setTextVersion((v) => v + 1)
    })
    return () => cancelAnimationFrame(id)
  }, [text])

  // Start delay
  useEffect(() => {
    if (!trigger || reducedMotion) return

    const timeout = setTimeout(() => setStarted(true), startDelay)
    return () => clearTimeout(timeout)
  }, [trigger, startDelay, reducedMotion, textVersion])

  // Typing animation
  useEffect(() => {
    if (!started || reducedMotion) return
    if (charIndex >= text.length) return

    intervalRef.current = setInterval(() => {
      setCharIndex((prev) => {
        if (prev >= text.length) {
          if (intervalRef.current) clearInterval(intervalRef.current)
          return prev
        }
        return prev + 1
      })
    }, speed)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [started, text, speed, reducedMotion, charIndex])

  // Blinking cursor
  useEffect(() => {
    if (reducedMotion) return

    cursorRef.current = setInterval(() => {
      setCursorVisible((v) => !v)
    }, 530)

    return () => {
      if (cursorRef.current) clearInterval(cursorRef.current)
    }
  }, [reducedMotion])

  if (reducedMotion) {
    return {
      displayText: text,
      isComplete: true,
      cursorVisible: false,
    }
  }

  return {
    displayText: text.slice(0, charIndex),
    isComplete: charIndex >= text.length,
    cursorVisible,
  }
}
