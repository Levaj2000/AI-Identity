import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import '@testing-library/jest-dom/vitest'
import { AgentKeysPage } from '../AgentKeysPage'

// ── Mock the hook ────────────────────────────────────────────────────

const mockRefetch = vi.fn()
const mockUseAgentKeys = vi.fn()
vi.mock('../../hooks/useAgentKeys', () => ({
  useAgentKeys: (...args: unknown[]) => mockUseAgentKeys(...args),
}))

// ── Mock API calls used directly by the page ─────────────────────────

const mockCreateKey = vi.fn()
const mockRotateKey = vi.fn()
const mockRevokeKey = vi.fn()
vi.mock('../../services/api/keys', () => ({
  createKey: (...args: unknown[]) => mockCreateKey(...args),
  rotateKey: (...args: unknown[]) => mockRotateKey(...args),
  revokeKey: (...args: unknown[]) => mockRevokeKey(...args),
}))

vi.mock('../../services/api/client', () => ({
  isApiError: (err: unknown) =>
    typeof err === 'object' && err !== null && 'status' in err && 'code' in err,
}))

// ── Mock child components ────────────────────────────────────────────

vi.mock('../../components/AgentStatusBadge', () => ({
  AgentStatusBadge: ({ status }: { status: string }) => (
    <span data-testid="status-badge">{status}</span>
  ),
}))
vi.mock('../../components/keys/KeyTable', () => ({
  KeyTable: ({
    keys,
    onRevoke,
  }: {
    keys: { id: number }[]
    isAgentRevoked: boolean
    onRevoke: (id: number) => void
  }) => (
    <div data-testid="key-table">
      {keys.length} keys
      {keys.map((k) => (
        <button key={k.id} onClick={() => onRevoke(k.id)} data-testid={`revoke-key-${k.id}`}>
          Revoke #{k.id}
        </button>
      ))}
    </div>
  ),
}))
vi.mock('../../components/modals/ApiKeyModal', () => ({
  ApiKeyModal: ({
    apiKey,
    onDismiss,
  }: {
    apiKey: string
    agentName: string
    onDismiss: () => void
  }) => (
    <div data-testid="api-key-modal">
      <span>{apiKey}</span>
      <button onClick={onDismiss}>Dismiss</button>
    </div>
  ),
}))
vi.mock('../../components/modals/RotateKeyModal', () => ({
  RotateKeyModal: ({ apiKey, onDismiss }: { apiKey: string; onDismiss: () => void }) => (
    <div data-testid="rotate-key-modal">
      <span>{apiKey}</span>
      <button onClick={onDismiss}>Dismiss</button>
    </div>
  ),
}))
vi.mock('../../components/modals/ConfirmModal', () => ({
  ConfirmModal: ({
    onConfirm,
    onCancel,
    title,
  }: {
    onConfirm: () => void
    onCancel: () => void
    title: string
  }) => (
    <div data-testid="confirm-modal">
      <span>{title}</span>
      <button onClick={onConfirm}>Confirm</button>
      <button onClick={onCancel}>CancelModal</button>
    </div>
  ),
}))

// ── Helpers ──────────────────────────────────────────────────────────

const AGENT_ID = 'aaaa-bbbb-cccc-dddd'

function renderPage(id: string = AGENT_ID) {
  return render(
    <MemoryRouter initialEntries={[`/agents/${id}/keys`]}>
      <Routes>
        <Route path="/agents/:id/keys" element={<AgentKeysPage />} />
        <Route path="/dashboard/agents" element={<div>Agents list</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

const mockAgent = {
  id: AGENT_ID,
  user_id: 'user-1',
  name: 'Support Bot',
  description: 'Test agent',
  status: 'active' as const,
  capabilities: ['chat_completion'],
  metadata: {},
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockKey1 = {
  id: 1,
  agent_id: AGENT_ID,
  key_prefix: 'aid_sk_a',
  key_type: 'runtime' as const,
  status: 'active' as const,
  expires_at: null,
  created_at: '2026-01-01T00:00:00Z',
}

const mockKey2 = {
  id: 2,
  agent_id: AGENT_ID,
  key_prefix: 'aid_sk_b',
  key_type: 'runtime' as const,
  status: 'revoked' as const,
  expires_at: null,
  created_at: '2026-01-01T00:00:00Z',
}

const defaultHookReturn = {
  agent: null,
  keys: [],
  totalKeys: 0,
  isLoading: false,
  error: null,
  notFound: false,
  refetch: mockRefetch,
}

beforeEach(() => {
  mockUseAgentKeys.mockReset()
  mockCreateKey.mockReset()
  mockRotateKey.mockReset()
  mockRevokeKey.mockReset()
  mockRefetch.mockReset()
})

// ── Tests ────────────────────────────────────────────────────────────

describe('AgentKeysPage', () => {
  it('shows loading skeleton while fetching', () => {
    mockUseAgentKeys.mockReturnValue({ ...defaultHookReturn, isLoading: true })
    renderPage()

    const pulseElements = document.querySelectorAll('.animate-pulse')
    expect(pulseElements.length).toBeGreaterThan(0)
    expect(screen.queryByTestId('key-table')).not.toBeInTheDocument()
  })

  it('shows not-found state when agent does not exist', () => {
    mockUseAgentKeys.mockReturnValue({ ...defaultHookReturn, notFound: true })
    renderPage()

    expect(screen.getByText('Agent Not Found')).toBeInTheDocument()
    expect(screen.getByText('Back to Agents')).toBeInTheDocument()
  })

  it('shows error state with message', () => {
    mockUseAgentKeys.mockReturnValue({
      ...defaultHookReturn,
      error: { status: 500, code: 'internal', message: 'Key fetch failed' },
    })
    renderPage()

    expect(screen.getByText('Unable to Load Keys')).toBeInTheDocument()
    expect(screen.getByText('Key fetch failed')).toBeInTheDocument()
  })

  it('shows empty state when no keys exist', () => {
    mockUseAgentKeys.mockReturnValue({
      ...defaultHookReturn,
      agent: mockAgent,
      keys: [],
    })
    renderPage()

    expect(screen.getByText('No API Keys Yet')).toBeInTheDocument()
    expect(screen.getByText('Create Key')).toBeInTheDocument()
  })

  it('renders key table with filter tabs and action buttons', () => {
    mockUseAgentKeys.mockReturnValue({
      ...defaultHookReturn,
      agent: mockAgent,
      keys: [mockKey1, mockKey2],
      totalKeys: 2,
    })
    renderPage()

    expect(screen.getByTestId('key-table')).toBeInTheDocument()
    expect(screen.getByText('Create Key')).toBeInTheDocument()
    expect(screen.getByText('Rotate')).toBeInTheDocument()

    // Filter tabs with counts
    expect(screen.getByText('All (2)')).toBeInTheDocument()
    expect(screen.getByText('Active (1)')).toBeInTheDocument()
    expect(screen.getByText('Revoked (1)')).toBeInTheDocument()
  })

  it('creates a key and shows the API key modal', async () => {
    mockUseAgentKeys.mockReturnValue({
      ...defaultHookReturn,
      agent: mockAgent,
      keys: [mockKey1],
      totalKeys: 1,
    })
    mockCreateKey.mockResolvedValue({
      key: { ...mockKey1, id: 3 },
      api_key: 'aid_sk_new_secret_key',
    })
    renderPage()

    fireEvent.click(screen.getByText('Create Key'))

    await waitFor(() => {
      expect(mockCreateKey).toHaveBeenCalledWith(AGENT_ID)
    })
    await waitFor(() => {
      expect(screen.getByTestId('api-key-modal')).toBeInTheDocument()
    })
    expect(screen.getByText('aid_sk_new_secret_key')).toBeInTheDocument()
  })

  it('dismisses create modal and refetches', async () => {
    mockUseAgentKeys.mockReturnValue({
      ...defaultHookReturn,
      agent: mockAgent,
      keys: [mockKey1],
      totalKeys: 1,
    })
    mockCreateKey.mockResolvedValue({
      key: mockKey1,
      api_key: 'aid_sk_xxx',
    })
    renderPage()

    fireEvent.click(screen.getByText('Create Key'))
    await waitFor(() => expect(screen.getByTestId('api-key-modal')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Dismiss'))
    expect(mockRefetch).toHaveBeenCalled()
  })

  it('rotates a key and shows the rotate modal', async () => {
    mockUseAgentKeys.mockReturnValue({
      ...defaultHookReturn,
      agent: mockAgent,
      keys: [mockKey1],
      totalKeys: 1,
    })
    mockRotateKey.mockResolvedValue({
      new_key: { ...mockKey1, id: 4, key_prefix: 'aid_sk_n' },
      api_key: 'aid_sk_rotated_key',
      rotated_key: { ...mockKey1, status: 'rotated', expires_at: '2026-03-18T00:00:00Z' },
    })
    renderPage()

    fireEvent.click(screen.getByText('Rotate'))

    await waitFor(() => {
      expect(mockRotateKey).toHaveBeenCalledWith(AGENT_ID)
    })
    await waitFor(() => {
      expect(screen.getByTestId('rotate-key-modal')).toBeInTheDocument()
    })
  })

  it('triggers revoke confirmation modal from key table', async () => {
    mockUseAgentKeys.mockReturnValue({
      ...defaultHookReturn,
      agent: mockAgent,
      keys: [mockKey1],
      totalKeys: 1,
    })
    mockRevokeKey.mockResolvedValue({ ...mockKey1, status: 'revoked' })
    renderPage()

    // Click revoke on key #1 (from mocked KeyTable)
    fireEvent.click(screen.getByTestId('revoke-key-1'))

    expect(screen.getByTestId('confirm-modal')).toBeInTheDocument()
    expect(screen.getByText('Revoke API Key')).toBeInTheDocument()

    // Confirm the revocation
    fireEvent.click(screen.getByText('Confirm'))

    await waitFor(() => {
      expect(mockRevokeKey).toHaveBeenCalledWith(AGENT_ID, 1)
    })
  })

  it('disables create and rotate for revoked agents', () => {
    const revokedAgent = { ...mockAgent, status: 'revoked' as const }
    mockUseAgentKeys.mockReturnValue({
      ...defaultHookReturn,
      agent: revokedAgent,
      keys: [{ ...mockKey1, status: 'revoked' as const }],
      totalKeys: 1,
    })
    renderPage()

    expect(screen.getByText(/This agent has been revoked/)).toBeInTheDocument()

    const createBtn = screen.getByText('Create Key').closest('button')
    const rotateBtn = screen.getByText('Rotate').closest('button')
    expect(createBtn).toBeDisabled()
    expect(rotateBtn).toBeDisabled()
  })

  it('shows action error when create fails', async () => {
    mockUseAgentKeys.mockReturnValue({
      ...defaultHookReturn,
      agent: mockAgent,
      keys: [mockKey1],
      totalKeys: 1,
    })
    mockCreateKey.mockRejectedValue({
      status: 500,
      code: 'internal',
      message: 'Key creation failed',
    })
    renderPage()

    fireEvent.click(screen.getByText('Create Key'))

    await waitFor(() => {
      expect(screen.getByText('Key creation failed')).toBeInTheDocument()
    })
  })
})
