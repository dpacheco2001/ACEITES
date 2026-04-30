import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './auth/ProtectedRoute.jsx'
import Layout from './components/Layout.jsx'
import Flota from './pages/Flota.jsx'
import Equipo from './pages/Equipo.jsx'
import Equipos from './pages/Equipos.jsx'
import NuevaMuestra from './pages/NuevaMuestra.jsx'
import Reportes from './pages/Reportes.jsx'
import Login from './pages/Login.jsx'
import AdminUsuarios from './pages/AdminUsuarios.jsx'

export default function App() {
  return (
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
          <Route path="/admin/usuarios" element={<AdminUsuarios />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
