/**
 * The one semantic this panel must not get wrong: a producer restart is a
 * boundary, not a loss. These tests pin that a new epoch on the same
 * stream renders as a labeled restart divider between two segments — each
 * scored on its own — and never as a gap alarm; and that a real
 * within-epoch gap DOES surface as one.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

import { EdgeStreamsPanel } from '../EdgeStreamsPanel'
import * as edgesApi from '../../../services/api/edges'

vi.mock('../../../services/api/edges', () => ({
  listEdges: vi.fn(),
  fetchEdgeStreams: vi.fn(),
}))

const listEdges = vi.mocked(edgesApi.listEdges)
const fetchEdgeStreams = vi.mocked(edgesApi.fetchEdgeStreams)

function edgeWith(segments: edgesApi.EdgeStreamSegment[], quarantined = 0) {
  return {
    edge_id: 'edge-1',
    name: 'Test Edge',
    chain_uid: 'chain-1',
    status: 'active',
    last_ingest_at: '2026-09-01T00:00:00Z',
    verified: segments.reduce((n, s) => n + s.records, 0),
    quarantined,
    segments,
  }
}

function segment(over: Partial<edgesApi.EdgeStreamSegment>): edgesApi.EdgeStreamSegment {
  return {
    stream_id: 'gw-1/boot-7',
    epoch: 1,
    first_seq: 0,
    last_seq: 1,
    records: 2,
    dense: true,
    anomaly_records: 0,
    last_received_at: '2026-09-01T00:00:00Z',
    ...over,
  }
}

describe('EdgeStreamsPanel — restart is a boundary, not a loss', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    listEdges.mockResolvedValue({
      edges: [{ id: 'edge-1' } as unknown as edgesApi.EdgeSummary],
    })
  })

  it('renders a restart divider between epochs of one stream, both dense, no alarm', async () => {
    fetchEdgeStreams.mockResolvedValue(
      edgeWith([
        segment({ epoch: 1, first_seq: 41, last_seq: 45, records: 5 }),
        segment({ epoch: 2, first_seq: 1, last_seq: 1, records: 1 }),
      ]),
    )
    render(<EdgeStreamsPanel />)

    expect(
      await screen.findByText(/producer restart — new epoch, counter reset is expected/),
    ).toBeInTheDocument()
    // Two segments, each scored dense on its own — the seq reset raised
    // no anomaly language anywhere.
    expect(screen.getAllByText(/dense/)).toHaveLength(2)
    expect(screen.queryByText(/anomal/)).not.toBeInTheDocument()
  })

  it('surfaces a real within-epoch gap with its anomaly count', async () => {
    fetchEdgeStreams.mockResolvedValue(
      edgeWith([
        segment({
          epoch: 2,
          first_seq: 0,
          last_seq: 3,
          records: 3,
          dense: false,
          anomaly_records: 1,
        }),
      ]),
    )
    render(<EdgeStreamsPanel />)

    expect(await screen.findByText(/3 of 4 · 1 anomaly/)).toBeInTheDocument()
    expect(screen.queryByText(/producer restart/)).not.toBeInTheDocument()
  })

  it('scores a restart that lost its first record as a head loss, not a full set', async () => {
    // Epoch 2 opens at seq 1: record 0 never arrived. The interior (1..2)
    // is dense, so counting from the first seen record would print
    // "2 of 2". The expected count is from 0, and the head loss is named.
    fetchEdgeStreams.mockResolvedValue(
      edgeWith([
        segment({ epoch: 1, first_seq: 0, last_seq: 1, records: 2 }),
        segment({
          epoch: 2,
          first_seq: 1,
          last_seq: 2,
          records: 2,
          dense: false,
          anomaly_records: 1,
        }),
      ]),
    )
    render(<EdgeStreamsPanel />)
    expect(await screen.findByText(/2 of 3 · head lost · 1 anomaly/)).toBeInTheDocument()
    expect(screen.getAllByText(/dense/)).toHaveLength(1)
  })

  it('shows quarantined records as their own count, outside any segment', async () => {
    fetchEdgeStreams.mockResolvedValue(edgeWith([segment({})], 1))
    render(<EdgeStreamsPanel />)

    expect(await screen.findByText(/1 quarantined/)).toBeInTheDocument()
  })

  it('renders nothing at all when the org has no edge deployments', async () => {
    listEdges.mockResolvedValue({ edges: [] })
    const { container } = render(<EdgeStreamsPanel />)
    await Promise.resolve()
    expect(container).toBeEmptyDOMElement()
  })
})
