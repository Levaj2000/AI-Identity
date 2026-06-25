/**
 * Component test for the wrong-file guard: dropping an evidence-anchor file on
 * the server-side Case File verifier should show a friendly, correctly-routed
 * hint WITHOUT uploading (no scary "Signature invalid" from the server).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

import { CaseFileVerifyPanel } from '../CaseFileVerifyPanel'

vi.mock('../../../services/api/client', () => ({
  getAuthHeaders: async () => ({ Authorization: 'Bearer test' }),
}))

function jsonFile(name: string, value: unknown): File {
  return new File([JSON.stringify(value)], name, { type: 'application/json' })
}

function fileInput(): HTMLInputElement {
  return document.querySelector('input[type="file"]') as HTMLInputElement
}

describe('CaseFileVerifyPanel — wrong-file guard', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('rejects a dropped checkpoints.json without uploading, and routes the user', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<CaseFileVerifyPanel />)
    fireEvent.change(fileInput(), {
      target: { files: [jsonFile('checkpoints.json', [{ merkle_root: 'a', envelope: {} }])] },
    })

    await waitFor(() =>
      expect(screen.getByText(/evidence-anchor file \(checkpoints\.json\)/)).toBeInTheDocument(),
    )
    expect(screen.getByText(/Verify event inclusion/)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('uploads a real Case File report (has events)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ verified: true, chain_intact: true, signature_valid: true }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<CaseFileVerifyPanel />)
    fireEvent.change(fileInput(), {
      target: { files: [jsonFile('case-file-foo.json', { report_id: 'r1', events: [] })] },
    })

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce())
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/audit/verify'),
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
