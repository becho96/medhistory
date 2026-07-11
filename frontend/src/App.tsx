import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'

// Pages
import Landing from './pages/Landing'
import LandingMoms from './pages/LandingMoms'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Documents from './pages/Documents'
import TreatmentPlan from './pages/TreatmentPlan'
import Reports from './pages/Reports'
import Labs from './pages/Labs'
import Interpretations from './pages/Interpretations'
import HealthEvents from './pages/HealthEvents'
import AssistantPage from './pages/AssistantPage'
import Integrations from './pages/Integrations'
import Profile from './pages/Profile'
import OAuthConsent from './pages/OAuthConsent'
import LegalPage from './pages/LegalPage'
import Subscription from './pages/Subscription'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminPromocodes from './pages/admin/Promocodes'
import AdminUsers from './pages/admin/Users'

// Layout
import Layout from './components/Layout/Layout'
import AdminRoute from './components/AdminRoute'

function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  return (
    <Routes>
      {/* MCP OAuth consent — gated by component itself; no Layout wrapper. */}
      <Route path="/oauth/consent" element={<OAuthConsent />} />

      {/* Legal documents — always accessible, no auth required */}
      <Route path="/legal/:slug" element={<LegalPage />} />

      {!isAuthenticated ? (
        <>
          <Route path="/" element={<Landing />} />
          <Route path="/deti" element={<LandingMoms />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </>
      ) : (
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/plan" element={<TreatmentPlan />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/health-events" element={<HealthEvents />} />
          <Route path="/interpretations" element={<Interpretations />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/labs" element={<Labs />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings/integrations" element={<Integrations />} />
          <Route path="/subscription" element={<Subscription />} />
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/promocodes" element={<AdminPromocodes />} />
            <Route path="/admin/users" element={<AdminUsers />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      )}
    </Routes>
  )
}

export default App
