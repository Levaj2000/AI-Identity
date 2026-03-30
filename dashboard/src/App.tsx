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
import { AdminUserDetailPage } from './pages/AdminUserDetailPage'
import { ApprovalsPage } from './pages/ApprovalsPage'
import { ShadowAgentsPage } from './pages/ShadowAgentsPage'
import { QAChecklistPage } from './pages/QAChecklistPage'
import { WebPropertiesPage } from './pages/WebPropertiesPage'
import { ForensicsPage } from './pages/ForensicsPage'
import { OrganizationPage } from './pages/OrganizationPage'

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
        <Route path="organization" element={<OrganizationPage />} />
        <Route path="usage" element={<UsageBillingPage />} />
        <Route path="compliance" element={<CompliancePage />} />
        <Route path="forensics" element={<ForensicsPage />} />
        <Route path="qa" element={<QAChecklistPage />} />
        <Route path="properties" element={<WebPropertiesPage />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="shadow-agents" element={<ShadowAgentsPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="admin/users/:id" element={<AdminUserDetailPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
