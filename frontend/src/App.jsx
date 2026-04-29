import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Flota from './pages/Flota.jsx'
import Equipo from './pages/Equipo.jsx'
import NuevaMuestra from './pages/NuevaMuestra.jsx'
import Reportes from './pages/Reportes.jsx'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Flota />} />
        <Route path="/equipo" element={<Navigate to="/" replace />} />
        <Route path="/equipo/:id" element={<Equipo />} />
        <Route path="/nueva-muestra" element={<NuevaMuestra />} />
        <Route path="/nueva-muestra/:id" element={<NuevaMuestra />} />
        <Route path="/reportes" element={<Reportes />} />
      </Routes>
    </Layout>
  )
}
