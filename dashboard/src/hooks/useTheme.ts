import { useContext } from 'react'
import { ThemeContext } from '../contexts/theme'
import type { ThemeContextValue } from '../contexts/theme'

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider')
  return ctx
}
