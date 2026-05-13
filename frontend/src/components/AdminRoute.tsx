import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function AdminRoute() {
  const user = useAuthStore((s) => s.user)
  if (!user?.is_admin) {
    return <Navigate to="/" replace />
  }
  return <Outlet />
}
