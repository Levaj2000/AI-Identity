/**
 * Component test for the in-browser inclusion verifier. Drives the real wiring:
 * file selection → classifyAnchorJson → fetch published JWKS (mocked) →
 * verifyInclusion (real crypto, real Python-signed vector) → rendered verdict.
 * Only the network fetch of the public JWKS is mocked; the crypto is real.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

import { InclusionProofPanel } from '../InclusionProofPanel'
import vector from '../../../lib/__tests__/fixtures/anchor-vector.json'

function jsonFile(name: string, value: unknown): File {
  return new File([JSON.stringify(value)], name, { type: 'application/json' })
}

const checkpointsFile = () => jsonFile('checkpoints.json', vector.checkpoints)
const proofsFile = () => jsonFile('inclusion-proofs.json', vector.inclusionProofs)

function fileInput(): HTMLInputElement {
  // The hidden <input type="file" multiple> the dropzone delegates to.
  return document.querySelector('input[type="file"]') as HTMLInputElement
}

describe('InclusionProofPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('verifies inclusion client-side using the published JWKS', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => vector.jwks,
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<InclusionProofPanel />)
    fireEvent.change(fileInput(), { target: { files: [checkpointsFile(), proofsFile()] } })

    await waitFor(() => expect(screen.getByText('INCLUSION VERIFIED')).toBeInTheDocument())
    expect(screen.getByText(/VERIFIED · event #1003/)).toBeInTheDocument()
    expect(screen.getByText(/published JWKS/)).toBeInTheDocument()
    // The JWKS was fetched from the well-known endpoint.
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/.well-known/ai-identity-public-keys.json'),
      expect.anything(),
    )
  })

  it('verifies fully offline when a pinned JWKS file is dropped (no fetch)', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<InclusionProofPanel />)
    fireEvent.change(fileInput(), {
      target: { files: [checkpointsFile(), proofsFile(), jsonFile('jwks.json', vector.jwks)] },
    })

    await waitFor(() => expect(screen.getByText('INCLUSION VERIFIED')).toBeInTheDocument())
    expect(screen.getByText(/pinned JWKS \(offline\)/)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows NOT VERIFIED when the checkpoint signature does not match the keys', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ keys: [] }) }),
    )

    render(<InclusionProofPanel />)
    fireEvent.change(fileInput(), { target: { files: [checkpointsFile(), proofsFile()] } })

    await waitFor(() => expect(screen.getByText('INCLUSION NOT VERIFIED')).toBeInTheDocument())
  })

  it('errors when only one of the two evidence-anchor files is provided', async () => {
    render(<InclusionProofPanel />)
    fireEvent.change(fileInput(), { target: { files: [checkpointsFile()] } })

    await waitFor(() =>
      expect(screen.getByText(/Drop both evidence-anchor files/)).toBeInTheDocument(),
    )
  })
})
