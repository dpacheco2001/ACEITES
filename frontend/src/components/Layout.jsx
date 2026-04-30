import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { BarChart3, ClipboardPlus, FileDown, Shield, Truck } from 'lucide-react'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import AtlasLauncher from './AtlasLauncher.jsx'

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

function TopNavLink({ to, label, icon: Icon, end = false }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
          isActive ? 'nav-active' : 'nav-inactive'
        }`
      }
    >
      {Icon && <Icon size={16} strokeWidth={2} />}
      {label}
    </NavLink>
  )
}

function MobileNavLink({ to, label, icon: Icon, end = false }) {
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
      {Icon && <Icon size={14} strokeWidth={2} />}
      {label}
    </NavLink>
  )
}

export default function Layout() {
  const navigate = useNavigate()
  const { profile, logout } = useAuth()
  const [health, setHealth] = useState(null)
  const [lastSync, setLastSync] = useState(new Date())

  const initials = profile?.email ? profile.email.slice(0, 2).toUpperCase() : '?'

  useEffect(() => {
    let alive = true
    const pull = () => {
      api.health()
        .then((h) => {
          if (alive) {
            setHealth(h)
            setLastSync(new Date())
          }
        })
        .catch(() => {
          if (alive) setHealth({ status: 'down' })
        })
    }
    pull()
    const timer = setInterval(pull, 30000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  const timeLabel = lastSync.toLocaleTimeString('es-PE', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background text-on-background antialiased">
      <header className="bg-glass shadow-ambient z-50 shrink-0">
        <div className="flex justify-between items-center w-full px-4 md:px-6 py-3">
          <div className="flex items-center space-x-4 md:space-x-6 min-w-0">
            <Link to="/" className="flex items-center gap-2 text-lg font-semibold tracking-tighter text-on-background truncate">
              <img src="/oilmine.svg" alt="" className="h-8 w-8 rounded-lg shrink-0" />
              <span className="truncate">OilMine Analytics</span>
            </Link>
            <nav className="hidden md:flex items-center gap-1" aria-label="Secciones principales">
              <TopNavLink to="/" label="Flota" icon={BarChart3} end />
              <TopNavLink to="/equipo" label="Equipo" icon={Truck} />
              <TopNavLink to="/nueva-muestra" label="Nueva Muestra" icon={ClipboardPlus} />
              <TopNavLink to="/reportes" label="Reportes" icon={FileDown} />
              {profile?.role === 'ADMIN' && (
                <TopNavLink to="/admin/usuarios" label="Usuarios" icon={Shield} />
              )}
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
            <div className="hidden sm:flex flex-col items-end text-right max-w-[180px]">
              <span className="text-[11px] font-mono truncate text-on-background" title={profile?.email}>
                {profile?.email || '-'}
              </span>
              <span className="text-[10px] uppercase tracking-wider text-on-surface-variant truncate max-w-[180px]">
                {profile?.role === 'ADMIN' ? 'Administrador' : 'Cliente'} - {profile?.tenant_key || ''}
              </span>
            </div>
            <button
              type="button"
              className="text-xs font-bold uppercase tracking-wider px-2 py-1 rounded-lg border border-outline-variant/60 hover:bg-surface-container-highest transition-colors"
              onClick={handleLogout}
            >
              Salir
            </button>
            <div
              className="w-8 h-8 rounded-full bg-primary-container text-on-primary flex items-center justify-center font-bold text-xs font-mono shrink-0"
              title={profile?.email || 'Usuario'}
            >
              {initials}
            </div>
          </div>
        </div>
      </header>

      <nav
        className="md:hidden flex gap-1 px-3 py-2 bg-surface-container-low overflow-x-auto no-scrollbar shrink-0"
        aria-label="Vistas móvil"
      >
        <MobileNavLink to="/" label="Flota" icon={BarChart3} end />
        <MobileNavLink to="/equipo" label="Equipo" icon={Truck} />
        <MobileNavLink to="/nueva-muestra" label="Muestra" icon={ClipboardPlus} />
        <MobileNavLink to="/reportes" label="Reportes" icon={FileDown} />
        {profile?.role === 'ADMIN' && (
          <MobileNavLink to="/admin/usuarios" label="Admin" icon={Shield} />
        )}
      </nav>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        <main className="flex-1 overflow-y-auto bg-surface min-w-0">
          <Outlet />
        </main>
      </div>
      <AtlasLauncher />
    </div>
  )
}
