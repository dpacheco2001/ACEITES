import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './auth/ProtectedRoute.jsx'
import Layout from './components/Layout.jsx'
import RouteErrorBoundary from './components/RouteErrorBoundary.jsx'

const Flota = lazy(() => import('./pages/Flota.jsx'))
const Equipo = lazy(() => import('./pages/Equipo.jsx'))
const Equipos = lazy(() => import('./pages/Equipos.jsx'))
const NuevaMuestra = lazy(() => import('./pages/NuevaMuestra.jsx'))
const Reportes = lazy(() => import('./pages/Reportes.jsx'))
const Login = lazy(() => import('./pages/Login.jsx'))
const AdminDatos = lazy(() => import('./pages/AdminDatos.jsx'))
const AdminUsuarios = lazy(() => import('./pages/AdminUsuarios.jsx'))
const OwnerOrganizaciones = lazy(() => import('./pages/OwnerOrganizaciones.jsx'))

function RouteFallback() {
  return <div className="p-6 text-sm text-on-surface-variant">Cargando vista...</div>
}

export default function App() {
  return (
    <RouteErrorBoundary>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Flota />} />
              <Route path="/equipo" element={<Equipos />} />
              <Route path="/equipo/:id" element={<Equipo />} />
              <Route path="/nueva-muestra" element={<NuevaMuestra />} />
              <Route path="/nueva-muestra/:id" element={<NuevaMuestra />} />
              <Route path="/reportes" element={<Reportes />} />
              <Route path="/admin/datos" element={<AdminDatos />} />
              <Route path="/admin/usuarios" element={<AdminUsuarios />} />
              <Route path="/owner/organizaciones" element={<OwnerOrganizaciones />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </RouteErrorBoundary>
  )
}
