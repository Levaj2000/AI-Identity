import { Routes, Route, Navigate } from 'react-router-dom'
import { DashboardLayout } from './layouts/DashboardLayout'
import { LandingPage } from './pages/LandingPage'
import { OverviewPage } from './pages/OverviewPage'
import { AgentsPage } from './pages/AgentsPage'
import { CreateAgentPage } from './pages/CreateAgentPage'
import { AgentDetailPage } from './pages/AgentDetailPage'
import { AgentKeysPage } from './pages/AgentKeysPage'
import { KeysPage } from './pages/KeysPage'
import { NotFoundPage } from './pages/NotFoundPage'

function App() {
  return (
    <Routes>
      {/* Marketing landing page — public, no layout wrapper */}
      <Route index element={<LandingPage />} />

      {/* Dashboard — wrapped in sidebar + header layout */}
      <Route path="app" element={<DashboardLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/new" element={<CreateAgentPage />} />
        <Route path="agents/:id" element={<AgentDetailPage />} />
        <Route path="agents/:id/keys" element={<AgentKeysPage />} />
        <Route path="keys" element={<KeysPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* Redirects — old dashboard routes → /app/* */}
      <Route path="agents/*" element={<Navigate to="/app/agents" replace />} />
      <Route path="keys" element={<Navigate to="/app/keys" replace />} />

      {/* Catch-all */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
