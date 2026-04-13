import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/layout/Layout'
import QueryPage from './pages/QueryPage'
import AuditPage from './pages/AuditPage'
import AdminPage from './pages/AdminPage'
import TATTrackerPage from './pages/TATTrackerPage'
import GraphPage from './pages/GraphPage'
import LoginPage from './pages/LoginPage'
import { useAuthStore } from './store/useAuthStore'

function ProtectedApp() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/query" replace />} />
        <Route path="/query" element={<QueryPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/tracker" element={<TATTrackerPage />} />
        <Route path="/graph" element={<GraphPage />} />
      </Routes>
    </Layout>
  )
}

export default function App() {
  const token = useAuthStore((state) => state.token)

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/*" element={token ? <ProtectedApp /> : <Navigate to="/login" replace />} />
    </Routes>
  )
}

