import { useScrollProgress } from '../../hooks/useScrollProgress'

/**
 * Animated architecture diagram with scroll-linked sequential reveal.
 * As the user scrolls, each component reveals in sequence:
 *   0.0–0.2: Agent box
 *   0.2–0.4: First arrow draws
 *   0.4–0.6: Gateway + sub-boxes
 *   0.6–0.8: Second arrow + External API
 *   0.8–1.0: Dashboard line + request dot
 */
export function ArchitectureSection() {
  const { ref, progress } = useScrollProgress()

  // Stage thresholds
  const stage1 = Math.min(1, Math.max(0, progress * 5)) // 0–0.2 → 0–1
  const stage2 = Math.min(1, Math.max(0, (progress - 0.2) * 5)) // 0.2–0.4 → 0–1
  const stage3 = Math.min(1, Math.max(0, (progress - 0.4) * 5)) // 0.4–0.6 → 0–1
  const stage4 = Math.min(1, Math.max(0, (progress - 0.6) * 5)) // 0.6–0.8 → 0–1
  const stage5 = Math.min(1, Math.max(0, (progress - 0.8) * 5)) // 0.8–1.0 → 0–1

  // Arrow dash offset: 1 (hidden) → 0 (fully drawn)
  const arrow1Offset = 1 - stage2
  const arrow2Offset = 1 - stage4

  return (
    <section id="how-it-works" className="min-h-[80vh] px-6 py-24">
      <div ref={ref} className="mx-auto max-w-5xl">
        {/* Header */}
        <div
          className="mb-16 text-center transition-all duration-700 ease-out"
          style={{ opacity: stage1, transform: `translateY(${(1 - stage1) * 24}px)` }}
        >
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-indigo-500/80 dark:text-indigo-400/80">
            How it works
          </p>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
            Drop-in proxy — zero code changes
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-gray-500 dark:text-slate-400">
            Point your agents at the gateway instead of the upstream API. Identity, policy, and
            audit happen transparently.
          </p>
        </div>

        {/* Diagram */}
        <div className="relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900/60 sm:p-10">
          <svg
            viewBox="0 0 800 320"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="w-full"
            role="img"
            aria-label="Architecture diagram showing Agent to Gateway to External API flow"
          >
            {/* ── Agent Box ── */}
            <g style={{ opacity: stage1, transition: 'opacity 0.4s ease' }}>
              <rect
                x="20"
                y="110"
                width="140"
                height="100"
                rx="12"
                className="fill-indigo-50 stroke-indigo-300 dark:fill-indigo-500/10 dark:stroke-indigo-500/40"
                strokeWidth="1.5"
                style={{
                  filter: stage1 > 0.5 ? 'drop-shadow(0 0 12px rgba(99,102,241,0.3))' : 'none',
                  transition: 'filter 0.5s ease',
                }}
              />
              <text
                x="90"
                y="150"
                textAnchor="middle"
                className="fill-indigo-600 dark:fill-indigo-400"
                fontSize="13"
                fontWeight="700"
              >
                Your Agent
              </text>
              <text
                x="90"
                y="172"
                textAnchor="middle"
                className="fill-gray-400 dark:fill-slate-500"
                fontSize="10"
                fontFamily="monospace"
              >
                aid_sk_a7f3…
              </text>
              <circle cx="90" cy="192" r="4" className="fill-amber-400" />
            </g>

            {/* ── Arrow: Agent → Gateway (draw-in) ── */}
            <g style={{ opacity: stage2 > 0 ? 1 : 0, transition: 'opacity 0.3s ease' }}>
              <line
                x1="160"
                y1="160"
                x2="260"
                y2="160"
                className="stroke-indigo-300 dark:stroke-indigo-500/50"
                strokeWidth="2"
                strokeDasharray="100"
                style={{ strokeDashoffset: arrow1Offset * 100 }}
              />
              <polygon
                points="258,154 270,160 258,166"
                className="fill-indigo-400 dark:fill-indigo-500"
                style={{ opacity: stage2 > 0.8 ? 1 : 0, transition: 'opacity 0.3s ease' }}
              />
            </g>

            {/* ── Gateway Box ── */}
            <g style={{ opacity: stage3, transition: 'opacity 0.5s ease' }}>
              <rect
                x="270"
                y="80"
                width="260"
                height="160"
                rx="14"
                className="fill-white stroke-indigo-400 dark:fill-slate-800/80 dark:stroke-indigo-500/60"
                strokeWidth="2"
                style={{
                  filter: stage3 > 0.5 ? 'drop-shadow(0 0 16px rgba(99,102,241,0.25))' : 'none',
                  transition: 'filter 0.5s ease',
                }}
              />
              <text
                x="400"
                y="108"
                textAnchor="middle"
                className="fill-indigo-600 dark:fill-indigo-400"
                fontSize="14"
                fontWeight="700"
              >
                AI Identity Gateway
              </text>
            </g>

            {/* Policy Engine sub-box — staggered within stage 3 */}
            <g
              style={{
                opacity: Math.min(1, Math.max(0, (stage3 - 0.2) / 0.8)),
                transition: 'opacity 0.3s ease',
              }}
            >
              <rect
                x="290"
                y="120"
                width="105"
                height="50"
                rx="8"
                className="fill-emerald-50 stroke-emerald-300 dark:fill-emerald-500/10 dark:stroke-emerald-500/40"
                strokeWidth="1"
              />
              <text
                x="342"
                y="142"
                textAnchor="middle"
                className="fill-emerald-700 dark:fill-emerald-400"
                fontSize="10"
                fontWeight="600"
              >
                Policy Engine
              </text>
              <text
                x="342"
                y="158"
                textAnchor="middle"
                className="fill-gray-400 dark:fill-slate-500"
                fontSize="9"
              >
                enforce / deny
              </text>
            </g>

            {/* Audit Log sub-box */}
            <g
              style={{
                opacity: Math.min(1, Math.max(0, (stage3 - 0.4) / 0.6)),
                transition: 'opacity 0.3s ease',
              }}
            >
              <rect
                x="405"
                y="120"
                width="105"
                height="50"
                rx="8"
                className="fill-amber-50 stroke-amber-300 dark:fill-amber-500/10 dark:stroke-amber-500/40"
                strokeWidth="1"
              />
              <text
                x="457"
                y="142"
                textAnchor="middle"
                className="fill-amber-700 dark:fill-amber-400"
                fontSize="10"
                fontWeight="600"
              >
                Audit Log
              </text>
              <text
                x="457"
                y="158"
                textAnchor="middle"
                className="fill-gray-400 dark:fill-slate-500"
                fontSize="9"
              >
                HMAC chain
              </text>
            </g>

            {/* Identity verification label */}
            <g
              style={{
                opacity: Math.min(1, Math.max(0, (stage3 - 0.6) / 0.4)),
                transition: 'opacity 0.3s ease',
              }}
            >
              <rect
                x="320"
                y="185"
                width="160"
                height="36"
                rx="8"
                className="fill-indigo-50 stroke-indigo-200 dark:fill-indigo-500/10 dark:stroke-indigo-500/30"
                strokeWidth="1"
              />
              <text
                x="400"
                y="207"
                textAnchor="middle"
                className="fill-indigo-600 dark:fill-indigo-400"
                fontSize="10"
                fontWeight="600"
              >
                Identity Verification
              </text>
            </g>

            {/* ── Arrow: Gateway → External API (draw-in) ── */}
            <g style={{ opacity: stage4 > 0 ? 1 : 0, transition: 'opacity 0.3s ease' }}>
              <line
                x1="530"
                y1="160"
                x2="620"
                y2="160"
                className="stroke-indigo-300 dark:stroke-indigo-500/50"
                strokeWidth="2"
                strokeDasharray="90"
                style={{ strokeDashoffset: arrow2Offset * 90 }}
              />
              <polygon
                points="618,154 630,160 618,166"
                className="fill-indigo-400 dark:fill-indigo-500"
                style={{ opacity: stage4 > 0.8 ? 1 : 0, transition: 'opacity 0.3s ease' }}
              />
            </g>

            {/* ── External API Box ── */}
            <g style={{ opacity: stage4, transition: 'opacity 0.5s ease' }}>
              <rect
                x="630"
                y="110"
                width="150"
                height="100"
                rx="12"
                className="fill-gray-50 stroke-gray-300 dark:fill-slate-800/50 dark:stroke-slate-600"
                strokeWidth="1.5"
              />
              <text
                x="705"
                y="150"
                textAnchor="middle"
                className="fill-gray-700 dark:fill-slate-300"
                fontSize="13"
                fontWeight="700"
              >
                External API
              </text>
              <text
                x="705"
                y="172"
                textAnchor="middle"
                className="fill-gray-400 dark:fill-slate-500"
                fontSize="10"
              >
                OpenAI, Stripe, …
              </text>
            </g>

            {/* ── Dashboard feedback line ── */}
            <g style={{ opacity: stage5, transition: 'opacity 0.5s ease' }}>
              <line
                x1="400"
                y1="240"
                x2="400"
                y2="290"
                className="stroke-gray-300 dark:stroke-slate-700"
                strokeWidth="1"
                strokeDasharray="50"
                style={{ strokeDashoffset: (1 - stage5) * 50 }}
              />
              <rect
                x="330"
                y="285"
                width="140"
                height="30"
                rx="6"
                className="fill-gray-50 stroke-gray-200 dark:fill-slate-800/60 dark:stroke-slate-700"
                strokeWidth="1"
              />
              <text
                x="400"
                y="305"
                textAnchor="middle"
                className="fill-gray-500 dark:fill-slate-400"
                fontSize="10"
                fontWeight="500"
              >
                Dashboard &amp; Alerts
              </text>
            </g>

            {/* ── Animated request dot (only after all stages complete) ── */}
            {stage5 > 0.8 && (
              <circle r="5" className="fill-amber-400" opacity="0.9">
                <animateMotion
                  dur="3s"
                  repeatCount="indefinite"
                  path="M90,160 L265,160 L400,160 L535,160 L705,160"
                />
                <animate
                  attributeName="opacity"
                  values="0;1;1;1;0"
                  dur="3s"
                  repeatCount="indefinite"
                />
              </circle>
            )}
          </svg>

          {/* Step labels */}
          <div className="mt-8 grid gap-4 text-center sm:grid-cols-3">
            {[
              {
                step: '1',
                label: 'Agent authenticates',
                desc: 'Uses its unique aid_sk_… key',
                stage: stage1,
              },
              {
                step: '2',
                label: 'Gateway enforces policy',
                desc: 'Checks permissions, logs the request',
                stage: stage3,
              },
              {
                step: '3',
                label: 'Request is proxied',
                desc: 'Upstream API sees a clean request',
                stage: stage4,
              },
            ].map((s) => (
              <div
                key={s.step}
                className="flex flex-col items-center transition-all duration-500"
                style={{ opacity: s.stage, transform: `translateY(${(1 - s.stage) * 16}px)` }}
              >
                <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-400">
                  {s.step}
                </div>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{s.label}</p>
                <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
