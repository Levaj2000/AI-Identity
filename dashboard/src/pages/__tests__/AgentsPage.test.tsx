import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import '@testing-library/jest-dom/vitest'
import { AgentsPage } from '../AgentsPage'

// ── Mock the hook ────────────────────────────────────────────────────

const mockUseAgentsList = vi.fn()
vi.mock('../../hooks/useAgentsList', () => ({
  useAgentsList: (...args: unknown[]) => mockUseAgentsList(...args),
}))

// ── Mock child components to keep tests focused on AgentsPage logic ──

vi.mock('../../components/agents/AgentFilters', () => ({
  AgentFilters: () => <div data-testid="agent-filters" />,
}))
vi.mock('../../components/agents/AgentTable', () => ({
  AgentTable: ({ agents }: { agents: unknown[] }) => (
    <div data-testid="agent-table">{agents.length} agents</div>
  ),
}))
vi.mock('../../components/agents/AgentCardGrid', () => ({
  AgentCardGrid: ({ agents }: { agents: unknown[] }) => (
    <div data-testid="agent-card-grid">{agents.length} agents</div>
  ),
}))
vi.mock('../../components/agents/AgentEmptyState', () => ({
  AgentEmptyState: () => <div data-testid="agent-empty-state">No agents found</div>,
}))
vi.mock('../../components/Pagination', () => ({
  Pagination: () => <div data-testid="pagination" />,
}))

// ── Helpers ──────────────────────────────────────────────────────────

function renderPage() {
  return render(
    <MemoryRouter>
      <AgentsPage />
    </MemoryRouter>,
  )
}

const mockAgent = {
  id: 'aaaa-bbbb-cccc-dddd',
  user_id: 'user-1',
  name: 'Test Bot',
  description: 'A test agent',
  status: 'active' as const,
  capabilities: ['chat_completion'],
  metadata: {},
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const defaultHookReturn = {
  agents: [],
  total: 0,
  isLoading: false,
  error: null,
  statusFilter: undefined,
  setStatusFilter: vi.fn(),
  capabilityFilter: '',
  setCapabilityFilter: vi.fn(),
  page: 1,
  setPage: vi.fn(),
  totalPages: 1,
  pageSize: 20,
}

beforeEach(() => {
  mockUseAgentsList.mockReset()
})

// ── Tests ────────────────────────────────────────────────────────────

describe('AgentsPage', () => {
  it('renders the page header and New Agent link', () => {
    mockUseAgentsList.mockReturnValue(defaultHookReturn)
    renderPage()

    expect(screen.getByText('Agents')).toBeInTheDocument()
    expect(screen.getByText('New Agent')).toBeInTheDocument()
    expect(screen.getByText('New Agent').closest('a')).toHaveAttribute(
      'href',
      '/dashboard/agents/new',
    )
  })

  it('shows loading skeletons while data is being fetched', () => {
    mockUseAgentsList.mockReturnValue({ ...defaultHookReturn, isLoading: true })
    renderPage()

    // Should show skeleton pulse elements, NOT the table or empty state
    expect(screen.queryByTestId('agent-table')).not.toBeInTheDocument()
    expect(screen.queryByTestId('agent-empty-state')).not.toBeInTheDocument()
    // Skeletons use animate-pulse class
    const pulseElements = document.querySelectorAll('.animate-pulse')
    expect(pulseElements.length).toBeGreaterThan(0)
  })

  it('shows error state with message for generic errors', () => {
    mockUseAgentsList.mockReturnValue({
      ...defaultHookReturn,
      error: { status: 500, code: 'internal_error', message: 'Server exploded' },
    })
    renderPage()

    expect(screen.getByText('Unable to Load Agents')).toBeInTheDocument()
    expect(screen.getByText('Server exploded')).toBeInTheDocument()
  })

  it('shows auth-specific error message for 401', () => {
    mockUseAgentsList.mockReturnValue({
      ...defaultHookReturn,
      error: { status: 401, code: 'unauthorized', message: 'Invalid key' },
    })
    renderPage()

    expect(screen.getByText('Authentication Failed')).toBeInTheDocument()
    expect(screen.getByText(/Check your API key configuration/)).toBeInTheDocument()
  })

  it('shows empty state when no agents and no filters', () => {
    mockUseAgentsList.mockReturnValue(defaultHookReturn)
    renderPage()

    expect(screen.getByTestId('agent-empty-state')).toBeInTheDocument()
  })

  it('renders the agent table when agents are returned', () => {
    mockUseAgentsList.mockReturnValue({
      ...defaultHookReturn,
      agents: [mockAgent, { ...mockAgent, id: 'eeee', name: 'Bot 2' }],
      total: 2,
    })
    renderPage()

    expect(screen.getByTestId('agent-table')).toBeInTheDocument()
    expect(screen.getByTestId('agent-table')).toHaveTextContent('2 agents')
  })

  it('shows pagination when totalPages > 1', () => {
    mockUseAgentsList.mockReturnValue({
      ...defaultHookReturn,
      agents: [mockAgent],
      total: 40,
      totalPages: 2,
    })
    renderPage()

    expect(screen.getByTestId('pagination')).toBeInTheDocument()
  })

  it('hides pagination when only 1 page', () => {
    mockUseAgentsList.mockReturnValue({
      ...defaultHookReturn,
      agents: [mockAgent],
      total: 1,
      totalPages: 1,
    })
    renderPage()

    expect(screen.queryByTestId('pagination')).not.toBeInTheDocument()
  })
})
