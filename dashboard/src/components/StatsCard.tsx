import type { ReactNode } from 'react'

interface StatsCardProps {
  label: string
  value: number
  icon: ReactNode
  accent?: string
}

export function StatsCard({ label, value, icon, accent = 'text-indigo-500' }: StatsCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 transition-colors hover:border-gray-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700">
      <div className={`mb-3 ${accent}`}>{icon}</div>
      <p className="text-3xl font-bold text-gray-900 font-[JetBrains_Mono,monospace] dark:text-slate-100">
        {value}
      </p>
      <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">{label}</p>
    </div>
  )
}
