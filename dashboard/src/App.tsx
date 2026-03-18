import { Routes, Route } from 'react-router-dom'
import { DashboardLayout } from './layouts/DashboardLayout'
import { OverviewPage } from './pages/OverviewPage'
import { AgentsPage } from './pages/AgentsPage'
import { CreateAgentPage } from './pages/CreateAgentPage'
import { AgentDetailPage } from './pages/AgentDetailPage'
import { AgentKeysPage } from './pages/AgentKeysPage'
import { KeysPage } from './pages/KeysPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { LoginPage } from './pages/LoginPage'
import { DemoPage } from './pages/DemoPage'
import { CompliancePage } from './pages/CompliancePage'
import { UsageBillingPage } from './pages/UsageBillingPage'

function App() {
  return (
    <Routes>
      {/* Public login/signup gate */}
      <Route index element={<LoginPage />} />
      <Route path="login" element={<LoginPage />} />

      {/* Public interactive demo */}
      <Route path="demo" element={<DemoPage />} />

      {/* Dashboard (will require auth later) */}
      <Route path="dashboard" element={<DashboardLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/new" element={<CreateAgentPage />} />
        <Route path="agents/:id" element={<AgentDetailPage />} />
        <Route path="agents/:id/keys" element={<AgentKeysPage />} />
        <Route path="keys" element={<KeysPage />} />
        <Route path="usage" element={<UsageBillingPage />} />
        <Route path="compliance" element={<CompliancePage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
