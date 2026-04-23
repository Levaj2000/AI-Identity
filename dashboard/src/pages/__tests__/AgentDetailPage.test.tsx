import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import '@testing-library/jest-dom/vitest'
import { AgentDetailPage } from '../AgentDetailPage'

// ── Mock the hook ────────────────────────────────────────────────────

const mockRefetch = vi.fn()
const mockUseAgentDetail = vi.fn()
vi.mock('../../hooks/useAgentDetail', () => ({
  useAgentDetail: (...args: unknown[]) => mockUseAgentDetail(...args),
}))

// ── Mock API calls used directly by the page ─────────────────────────

const mockUpdateAgent = vi.fn()
const mockDeleteAgent = vi.fn()
vi.mock('../../services/api/agents', () => ({
  updateAgent: (...args: unknown[]) => mockUpdateAgent(...args),
  deleteAgent: (...args: unknown[]) => mockDeleteAgent(...args),
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
vi.mock('../../components/forms/TagInput', () => ({
  TagInput: () => <div data-testid="tag-input" />,
}))
vi.mock('../../components/forms/KeyValueEditor', () => ({
  KeyValueEditor: () => <div data-testid="kv-editor" />,
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
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}))

// ── Helpers ──────────────────────────────────────────────────────────

const AGENT_ID = 'aaaa-bbbb-cccc-dddd'

function renderPage(id: string = AGENT_ID) {
  return render(
    <MemoryRouter initialEntries={[`/agents/${id}`]}>
      <Routes>
        <Route path="/agents/:id" element={<AgentDetailPage />} />
        <Route path="/dashboard/agents" element={<div>Agents list</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

const mockAgent = {
  id: AGENT_ID,
  user_id: 'user-1',
  name: 'Support Bot',
  description: 'Handles tier-1 support tickets',
  status: 'active' as const,
  capabilities: ['chat_completion', 'function_calling'],
  metadata: { framework: 'langchain', env: 'production' },
  eu_ai_act_risk_class: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-03-01T00:00:00Z',
}

const defaultHookReturn = {
  agent: null,
  isLoading: false,
  error: null,
  notFound: false,
  refetch: mockRefetch,
}

beforeEach(() => {
  mockUseAgentDetail.mockReset()
  mockUpdateAgent.mockReset()
  mockDeleteAgent.mockReset()
  mockRefetch.mockReset()
})

// ── Tests ────────────────────────────────────────────────────────────

describe('AgentDetailPage', () => {
  it('shows loading skeleton while fetching', () => {
    mockUseAgentDetail.mockReturnValue({ ...defaultHookReturn, isLoading: true })
    renderPage()

    const pulseElements = document.querySelectorAll('.animate-pulse')
    expect(pulseElements.length).toBeGreaterThan(0)
    expect(screen.queryByText('Support Bot')).not.toBeInTheDocument()
  })

  it('shows not-found state when agent does not exist', () => {
    mockUseAgentDetail.mockReturnValue({ ...defaultHookReturn, notFound: true })
    renderPage()

    expect(screen.getByText('Agent Not Found')).toBeInTheDocument()
    expect(screen.getByText('Back to Agents')).toBeInTheDocument()
  })

  it('shows error state with message', () => {
    mockUseAgentDetail.mockReturnValue({
      ...defaultHookReturn,
      error: { status: 500, code: 'internal', message: 'Database error' },
    })
    renderPage()

    expect(screen.getByText('Unable to Load Agent')).toBeInTheDocument()
    expect(screen.getByText('Database error')).toBeInTheDocument()
  })

  it('renders agent details in view mode', () => {
    mockUseAgentDetail.mockReturnValue({ ...defaultHookReturn, agent: mockAgent })
    renderPage()

    // Name appears in breadcrumb + h1
    const nameMatches = screen.getAllByText('Support Bot')
    expect(nameMatches.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByRole('heading', { name: 'Support Bot' })).toBeInTheDocument()
    expect(screen.getByText('Handles tier-1 support tickets')).toBeInTheDocument()
    expect(screen.getByText('chat_completion')).toBeInTheDocument()
    expect(screen.getByText('function_calling')).toBeInTheDocument()
    expect(screen.getByTestId('status-badge')).toHaveTextContent('active')
    expect(screen.getByText('Edit')).toBeInTheDocument()
    expect(screen.getByText('Manage Keys')).toBeInTheDocument()
    expect(screen.getByText('Revoke')).toBeInTheDocument()
  })

  it('shows revoked banner and hides action buttons for revoked agents', () => {
    const revokedAgent = { ...mockAgent, status: 'revoked' as const }
    mockUseAgentDetail.mockReturnValue({ ...defaultHookReturn, agent: revokedAgent })
    renderPage()

    expect(screen.getByText(/This agent has been revoked/)).toBeInTheDocument()
    expect(screen.queryByText('Edit')).not.toBeInTheDocument()
    expect(screen.queryByText('Suspend')).not.toBeInTheDocument()
    expect(screen.queryByText('Revoke')).not.toBeInTheDocument()
  })

  it('enters edit mode and shows save/cancel buttons', () => {
    mockUseAgentDetail.mockReturnValue({ ...defaultHookReturn, agent: mockAgent })
    renderPage()

    fireEvent.click(screen.getByText('Edit'))

    expect(screen.getByText('Save Changes')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
    expect(screen.queryByText('Edit')).not.toBeInTheDocument()
  })

  it('calls updateAgent on save and refetches', async () => {
    mockUseAgentDetail.mockReturnValue({ ...defaultHookReturn, agent: mockAgent })
    mockUpdateAgent.mockResolvedValue({ ...mockAgent, name: 'Updated Bot' })
    renderPage()

    // Enter edit mode
    fireEvent.click(screen.getByText('Edit'))

    // Change the name
    const nameInput = screen.getByDisplayValue('Support Bot')
    fireEvent.change(nameInput, { target: { value: 'Updated Bot' } })

    // Save
    fireEvent.click(screen.getByText('Save Changes'))

    await waitFor(() => {
      expect(mockUpdateAgent).toHaveBeenCalledWith(AGENT_ID, { name: 'Updated Bot' })
    })
    await waitFor(() => {
      expect(mockRefetch).toHaveBeenCalled()
    })
  })

  it('opens revoke modal and calls deleteAgent on confirm', async () => {
    mockUseAgentDetail.mockReturnValue({ ...defaultHookReturn, agent: mockAgent })
    mockDeleteAgent.mockResolvedValue(mockAgent)
    renderPage()

    // Click Revoke button
    fireEvent.click(screen.getByText('Revoke'))
    expect(screen.getByTestId('confirm-modal')).toBeInTheDocument()
    expect(screen.getByText('Revoke Agent')).toBeInTheDocument()

    // Confirm revocation
    fireEvent.click(screen.getByText('Confirm'))

    await waitFor(() => {
      expect(mockDeleteAgent).toHaveBeenCalledWith(AGENT_ID)
    })
  })

  it('shows suspend button for active agents and activate for suspended', () => {
    mockUseAgentDetail.mockReturnValue({ ...defaultHookReturn, agent: mockAgent })
    renderPage()
    expect(screen.getByText('Suspend')).toBeInTheDocument()

    // Re-render with suspended agent
    mockUseAgentDetail.mockReturnValue({
      ...defaultHookReturn,
      agent: { ...mockAgent, status: 'suspended' as const },
    })
    renderPage()
    expect(screen.getByText('Activate')).toBeInTheDocument()
  })
})
