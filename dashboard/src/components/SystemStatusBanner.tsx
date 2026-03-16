function MiniSparkline() {
  const points = [18, 22, 19, 23]
  const max = 30
  const width = 48
  const height = 16
  const path = points
    .map((v, i) => {
      const x = (i / (points.length - 1)) * width
      const y = height - (v / max) * height
      return `${i === 0 ? 'M' : 'L'}${x},${y}`
    })
    .join(' ')

  return (
    <svg width={width} height={height} className="inline-block align-middle">
      <path
        d={path}
        fill="none"
        stroke="#F59E0B"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function SystemStatusBanner() {
  return (
    <div className="rounded-xl border border-l-4 border-gray-200 border-l-emerald-500 bg-white p-5 dark:border-[#F59E0B]/10 dark:border-l-emerald-500 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {/* Gateway Status */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
            Gateway Status
          </p>
          <div className="mt-1 flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span
                className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75"
                style={{ animationDuration: '2s' }}
              />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
            </span>
            <span className="font-semibold text-gray-900 dark:text-[#e4e4e7]">Operational</span>
          </div>
        </div>

        {/* API Latency */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
            API Latency
          </p>
          <div className="mt-1 flex items-center gap-2">
            <span className="font-semibold text-gray-900 dark:text-[#e4e4e7]">23ms</span>
            <MiniSparkline />
          </div>
        </div>

        {/* Uptime */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
            Uptime
          </p>
          <p className="mt-1 font-semibold text-emerald-500">99.97%</p>
        </div>

        {/* Last Key Rotation */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
            Last Key Rotation
          </p>
          <div className="mt-1 flex items-center gap-2">
            <svg
              className="h-4 w-4 text-gray-400 dark:text-[#71717a]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="font-semibold text-gray-900 dark:text-[#e4e4e7]">3 days ago</span>
          </div>
        </div>
      </div>
    </div>
  )
}
