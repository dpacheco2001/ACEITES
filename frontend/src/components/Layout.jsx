import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { api } from '../api.js'

/**
 * Shell global: top-bar glass + sidebar desktop + tabs móvil.
 * La navegación primaria dirige a las 4 vistas del backend.
 */

// --- Iconos Material Symbols helpers ---
function MSIcon({ name, className = '', filled = false, style }) {
  const base = {
    fontVariationSettings: `'FILL' ${filled ? 1 : 0}, 'wght' 400, 'GRAD' 0, 'opsz' 24`,
    ...style,
  }
  return (
    <span className={`material-symbols-outlined ${className}`} style={base} aria-hidden>
      {name}
    </span>
  )
}
export { MSIcon }

// --- Botón de navegación con estilos activo/inactivo ---
function SideNavLink({ to, icon, label, end = false }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `w-full flex items-center px-3 py-2.5 rounded-lg text-left text-[11px] font-bold uppercase tracking-[0.05em] transition-all active:scale-[0.98] ${
          isActive ? 'nav-active' : 'nav-inactive'
        }`
      }
    >
      <MSIcon name={icon} className="mr-3 text-lg" />
      {label}
    </NavLink>
  )
}

function TopNavLink({ to, label, end = false }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
          isActive ? 'nav-active' : 'nav-inactive'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

function MobileNavLink({ to, label, end = false }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-bold uppercase tracking-wider whitespace-nowrap shrink-0 ${
          isActive ? 'nav-active' : 'nav-inactive'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

export default function Layout({ children }) {
  const loc = useLocation()
  const [health, setHealth] = useState(null)
  const [lastSync, setLastSync] = useState(new Date())

  // Refresca el health cada 30s para el pulso del topbar
  useEffect(() => {
    let alive = true
    const pull = () => {
      api.health()
        .then((h) => { if (alive) { setHealth(h); setLastSync(new Date()) } })
        .catch(() => { if (alive) setHealth({ status: 'down' }) })
    }
    pull()
    const t = setInterval(pull, 30000)
    return () => { alive = false; clearInterval(t) }
  }, [])

  // Si la ruta es /equipo/:id, la vista "Equipo" queda activa
  const equipoActive = loc.pathname.startsWith('/equipo')

  const timeLabel = lastSync.toLocaleTimeString('es-PE', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  })

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background text-on-background antialiased">
      {/* =================== TOP BAR (glassmorphism) =================== */}
      <header className="bg-glass shadow-ambient z-50 shrink-0">
        <div className="flex justify-between items-center w-full px-4 md:px-6 py-3">
          <div className="flex items-center space-x-4 md:space-x-6 min-w-0">
            <Link to="/" className="text-lg font-semibold tracking-tighter text-on-background truncate">
              OilMine Analytics
            </Link>
            <nav className="hidden md:flex items-center gap-1" aria-label="Secciones principales">
              <TopNavLink to="/"  label="Flota" end />
              {/* El link a "Equipo" lo activa la ruta /equipo/:id */}
              <NavLink
                to={equipoActive ? loc.pathname : '/equipo'}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  equipoActive ? 'nav-active' : 'nav-inactive'
                }`}
              >
                Equipo
              </NavLink>
              <TopNavLink to="/nueva-muestra" label="Nueva Muestra" />
              <TopNavLink to="/reportes" label="Reportes" />
            </nav>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="hidden sm:inline-flex items-center gap-2 text-sm telemetry-font text-on-background">
              <span
                className={`w-2 h-2 rounded-full ${health?.status === 'ok' ? 'bg-surface-tint' : 'bg-error'}`}
                title={health?.status === 'ok' ? 'API OK' : 'API caída'}
              />
              Last Sync: {timeLabel}
            </span>
            <button
              type="button"
              className="material-symbols-outlined text-on-background hover:opacity-70 transition-opacity"
              aria-label="Notificaciones"
            >notifications</button>
            <div
              className="w-8 h-8 rounded-full bg-primary-container text-on-primary flex items-center justify-center font-bold text-xs font-mono"
              title="Ingeniero de mantenimiento"
            >AD</div>
          </div>
        </div>
      </header>

      {/* =================== MOBILE SEGMENT (tabs) =================== */}
      <nav
        className="md:hidden flex gap-1 px-3 py-2 bg-surface-container-low overflow-x-auto no-scrollbar shrink-0"
        aria-label="Vistas móvil"
      >
        <MobileNavLink to="/"              label="Flota" end />
        <NavLink
          to={equipoActive ? loc.pathname : '/equipo'}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-bold uppercase tracking-wider whitespace-nowrap shrink-0 ${
            equipoActive ? 'nav-active' : 'nav-inactive'
          }`}
        >Equipo</NavLink>
        <MobileNavLink to="/nueva-muestra" label="Muestra" />
        <MobileNavLink to="/reportes"      label="Reportes" />
      </nav>

      {/* =================== MAIN SHELL =================== */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* ---- Sidebar desktop ---- */}
        <aside className="hidden md:flex flex-col h-full w-64 p-4 space-y-2 bg-surface-container-low shrink-0 z-40">
          <div className="mb-6 px-2">
            <h2 className="text-on-background font-headline font-bold text-sm tracking-tight">
              Mining Ops
            </h2>
            <p className="text-on-surface-variant font-mono text-[10px] uppercase tracking-widest mt-1">
              Technical Journal
            </p>
          </div>
          <nav className="flex-1 space-y-1" aria-label="Navegación lateral">
            <SideNavLink to="/"              icon="local_shipping"          label="Flota" end />
            <NavLink
              to={equipoActive ? loc.pathname : '/equipo'}
              className={`w-full flex items-center px-3 py-2.5 rounded-lg text-left text-[11px] font-bold uppercase tracking-[0.05em] transition-all active:scale-[0.98] ${
                equipoActive ? 'nav-active' : 'nav-inactive'
              }`}
            >
              <MSIcon name="precision_manufacturing" className="mr-3 text-lg" />
              Equipo
            </NavLink>
            <SideNavLink to="/nueva-muestra" icon="add_chart"               label="Nueva Muestra" />
            <SideNavLink to="/reportes"      icon="analytics"               label="Reportes" />
          </nav>

          {/* Pill de estado del backend al pie */}
          <div className="px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant/40 flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${health?.status === 'ok' ? 'bg-surface-tint' : 'bg-error'}`}
            />
            <span className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">
              {health?.status === 'ok'
                ? (health.modelos_cargados ? 'API · 3 modelos' : 'API · sin modelos')
                : 'API desconectada'}
            </span>
          </div>
        </aside>

        {/* ---- Contenido ---- */}
        <main className="flex-1 overflow-y-auto bg-surface min-w-0">
          {children}
        </main>
      </div>
    </div>
  )
}
