import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'

export default function ProtectedRoute() {
  const { profile, isAuthenticated, loading } = useAuth()
  const loc = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center bg-background text-on-background">
        <p className="text-sm text-on-surface-variant">Cargando sesión...</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  }

  if (
    profile?.role === 'ADMIN' &&
    profile?.dataset_loaded === false &&
    loc.pathname !== '/admin/datos' &&
    !loc.pathname.startsWith('/owner')
  ) {
    return <Navigate to="/admin/datos" replace />
  }

  return <Outlet />
}
