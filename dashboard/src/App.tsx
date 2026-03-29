import { Routes, Route } from 'react-router-dom'
import { DashboardLayout } from './layouts/DashboardLayout'
import { ProtectedRoute } from './components/ProtectedRoute'
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
import { AdminPage } from './pages/AdminPage'
import { QAChecklistPage } from './pages/QAChecklistPage'
import { WebPropertiesPage } from './pages/WebPropertiesPage'

function App() {
  return (
    <Routes>
      {/* Public routes — no auth required */}
      <Route index element={<LoginPage />} />
      <Route path="login" element={<LoginPage />} />
      <Route path="demo" element={<DemoPage />} />

      {/* Protected dashboard — requires valid API key */}
      <Route
        path="dashboard"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<OverviewPage />} />
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/new" element={<CreateAgentPage />} />
        <Route path="agents/:id" element={<AgentDetailPage />} />
        <Route path="agents/:id/keys" element={<AgentKeysPage />} />
        <Route path="keys" element={<KeysPage />} />
        <Route path="usage" element={<UsageBillingPage />} />
        <Route path="compliance" element={<CompliancePage />} />
        <Route path="qa" element={<QAChecklistPage />} />
        <Route path="properties" element={<WebPropertiesPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
