/**
 * Edge stream continuity — the read surface for work ingest already does.
 *
 * Every record arriving from an edge enforcement point is verified on
 * arrival (signature, fingerprint, chain, stream density) and continuity
 * anomalies are written on the rows. Until this panel, that verdict went
 * nowhere a person could see it without a database query.
 *
 * The one semantic this panel must not get wrong: a producer RESTART is a
 * boundary, not a loss. The emitter defines stream_seq as dense within
 * (epoch, stream_id); a new epoch legitimately resets the counter. So a
 * restart renders as a labeled boundary between two segments — each dense
 * on its own — never as a gap alarm. Crying wolf on the one event (a
 * crash) the stream is designed to survive would teach operators to
 * ignore the panel exactly when it matters.
 *
 * Renders nothing when the org has no edge deployments: no fabricated
 * surface for a feature not in use.
 */
import { useEffect, useState } from 'react'

import {
  fetchEdgeStreams,
  listEdges,
  type EdgeStreamSegment,
  type EdgeStreamsResponse,
} from '../../services/api/edges'

const tabular = { fontVariantNumeric: 'tabular-nums' as const }

function SegmentRow({ seg }: { seg: EdgeStreamSegment }) {
  // An epoch opens at stream_seq 0, so a segment holds last+1 records when
  // nothing was lost — counted from 0, not from wherever it happened to
  // start, or a lost head (records 0..first-1) would read as a full set.
  const expected = seg.last_seq + 1
  const lostHead = seg.first_seq > 0
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <div className="flex min-w-0 items-center gap-2">
        <span
          className={`inline-flex h-2 w-2 shrink-0 rounded-full ${
            seg.dense ? 'bg-success' : 'bg-warning'
          }`}
          aria-hidden
        />
        <span className="truncate text-sm text-ink">{seg.stream_id}</span>
        <span className="shrink-0 text-xs text-faint" style={tabular}>
          {seg.epoch !== null ? `epoch ${seg.epoch}` : 'no epoch'}
        </span>
      </div>
      <div className="shrink-0 text-right text-xs" style={tabular}>
        <span className="text-subtle">
          seq {seg.first_seq}–{seg.last_seq}
        </span>{' '}
        {seg.dense ? (
          <span className="text-success">dense · {seg.records} records</span>
        ) : (
          <span className="text-warning">
            {seg.records} of {expected}
            {lostHead ? ' · head lost' : ''} · {seg.anomaly_records}{' '}
            {seg.anomaly_records === 1 ? 'anomaly' : 'anomalies'}
          </span>
        )}
      </div>
    </div>
  )
}

function EdgeCard({ edge }: { edge: EdgeStreamsResponse }) {
  // Segments arrive oldest-epoch-first per stream; a change of epoch
  // within one stream is a restart boundary worth naming on screen.
  const byStream = new Map<string, EdgeStreamSegment[]>()
  for (const seg of edge.segments) {
    const list = byStream.get(seg.stream_id) ?? []
    list.push(seg)
    byStream.set(seg.stream_id, list)
  }

  return (
    <div className="rounded-lg border border-line bg-elevated p-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <span className="text-sm font-medium text-ink">{edge.name}</span>{' '}
          <span className="text-xs text-faint">· chain {edge.chain_uid}</span>
        </div>
        <div className="shrink-0 text-xs" style={tabular}>
          <span className="text-success">{edge.verified} verified</span>
          {edge.quarantined > 0 && (
            <span className="ml-2 rounded-full bg-danger-soft px-2 py-0.5 text-danger">
              {edge.quarantined} quarantined
            </span>
          )}
        </div>
      </div>

      {edge.segments.length === 0 ? (
        <p className="text-xs text-subtle">No stream records ingested yet.</p>
      ) : (
        [...byStream.entries()].map(([streamId, segments]) => (
          <div key={streamId} className="divide-y divide-line">
            {segments.map((seg, i) => (
              <div key={`${seg.epoch ?? 'none'}-${seg.first_seq}`}>
                {i > 0 && (
                  <div className="flex items-center gap-2 py-1 text-[11px] text-faint">
                    <span className="h-px flex-1 border-t border-dashed border-line" />
                    producer restart — new epoch, counter reset is expected
                    <span className="h-px flex-1 border-t border-dashed border-line" />
                  </div>
                )}
                <SegmentRow seg={seg} />
              </div>
            ))}
          </div>
        ))
      )}
    </div>
  )
}

export function EdgeStreamsPanel() {
  const [edges, setEdges] = useState<EdgeStreamsResponse[] | null>(null)

  useEffect(() => {
    let cancelled = false
    listEdges()
      .then((r) => Promise.all(r.edges.map((e) => fetchEdgeStreams(e.id))))
      .then((streams) => {
        if (!cancelled) setEdges(streams)
      })
      .catch(() => {
        // No surface for orgs without access to the edges API (non-admins)
        // or with nothing registered — absence, not an error banner.
        if (!cancelled) setEdges([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (!edges || edges.length === 0) return null

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <div className="mb-4">
        <h2 className="text-sm font-medium text-ink">Edge stream continuity</h2>
        <p className="text-xs text-subtle">
          Signed records from off-platform enforcement points, verified on arrival — density is per
          epoch, so a restart is a boundary, not a loss
        </p>
      </div>
      <div className="space-y-3">
        {edges.map((e) => (
          <EdgeCard key={e.edge_id} edge={e} />
        ))}
      </div>
    </div>
  )
}
