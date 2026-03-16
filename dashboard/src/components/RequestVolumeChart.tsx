import { useState } from 'react'

const mockData = [
  { day: 'Mon', requests: 1240 },
  { day: 'Tue', requests: 1890 },
  { day: 'Wed', requests: 2150 },
  { day: 'Thu', requests: 1780 },
  { day: 'Fri', requests: 2430 },
  { day: 'Sat', requests: 980 },
  { day: 'Sun', requests: 1560 },
]

const total = mockData.reduce((sum, d) => sum + d.requests, 0)
const peak = Math.max(...mockData.map((d) => d.requests))
const avg = Math.round(total / mockData.length)

export function RequestVolumeChart() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const padding = { top: 20, right: 20, bottom: 30, left: 20 }
  const chartHeight = 200
  const chartWidth = 500
  const innerWidth = chartWidth - padding.left - padding.right
  const innerHeight = chartHeight - padding.top - padding.bottom

  const maxVal = Math.max(...mockData.map((d) => d.requests)) * 1.1
  const points = mockData.map((d, i) => ({
    x: padding.left + (i / (mockData.length - 1)) * innerWidth,
    y: padding.top + innerHeight - (d.requests / maxVal) * innerHeight,
  }))

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
  const areaPath = `${linePath} L${points[points.length - 1].x},${padding.top + innerHeight} L${points[0].x},${padding.top + innerHeight} Z`

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">
            Request Volume
          </h2>
          <p className="text-sm text-gray-500 dark:text-[#71717a]">Last 7 days</p>
        </div>
        <span className="text-2xl font-bold text-[#F59E0B]">{total.toLocaleString()}</span>
      </div>

      <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full" style={{ height: 200 }}>
        <defs>
          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#F59E0B" stopOpacity="0" />
          </linearGradient>
        </defs>

        <path d={areaPath} fill="url(#areaGradient)" />
        <path
          d={linePath}
          fill="none"
          stroke="#F59E0B"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {points.map((p, i) => (
          <g key={i}>
            <circle
              cx={p.x}
              cy={p.y}
              r={hoveredIndex === i ? 5 : 3.5}
              fill="#F59E0B"
              stroke="#0A0A0B"
              strokeWidth="2"
              className="cursor-pointer transition-all"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            />
            {/* Larger invisible hit target */}
            <circle
              cx={p.x}
              cy={p.y}
              r={16}
              fill="transparent"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            />
            {hoveredIndex === i && (
              <g>
                <rect
                  x={p.x - 30}
                  y={p.y - 30}
                  width="60"
                  height="22"
                  rx="4"
                  fill="#1a1a1d"
                  stroke="#F59E0B"
                  strokeWidth="0.5"
                />
                <text
                  x={p.x}
                  y={p.y - 15}
                  textAnchor="middle"
                  fill="#F59E0B"
                  fontSize="12"
                  fontWeight="600"
                >
                  {mockData[i].requests.toLocaleString()}
                </text>
              </g>
            )}
            <text
              x={p.x}
              y={padding.top + innerHeight + 18}
              textAnchor="middle"
              fill="#71717a"
              fontSize="11"
            >
              {mockData[i].day}
            </text>
          </g>
        ))}
      </svg>

      <div className="mt-4 flex items-center justify-between border-t border-gray-200 pt-4 text-sm dark:border-[#1a1a1d]">
        <span className="text-gray-500 dark:text-[#71717a]">
          Peak:{' '}
          <span className="font-medium text-gray-900 dark:text-[#e4e4e7]">
            {peak.toLocaleString()}
          </span>
        </span>
        <span className="text-gray-500 dark:text-[#71717a]">
          Avg:{' '}
          <span className="font-medium text-gray-900 dark:text-[#e4e4e7]">
            {avg.toLocaleString()}
          </span>
        </span>
        <span className="text-gray-500 dark:text-[#71717a]">
          Total:{' '}
          <span className="font-medium text-gray-900 dark:text-[#e4e4e7]">
            {total.toLocaleString()}
          </span>
        </span>
      </div>
    </div>
  )
}
