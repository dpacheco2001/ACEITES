import { useEffect, useMemo, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Search, Truck } from 'lucide-react'
import { api } from '../api.js'
import { temaSemaforo, fmtHorasAceite } from '../semaforo_theme.js'

const SEVERITY = { ROJO: 0, AMARILLO: 1, VERDE: 2 }

export default function EquipoRail({ activeId }) {
  const [data, setData] = useState(null)
  const [query, setQuery] = useState('')
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    api.resumenFlota()
      .then((res) => {
        if (alive) setData(res)
      })
      .catch((error) => {
        if (alive) setErr(error.message)
      })
    return () => {
      alive = false
    }
  }, [])

  const equipos = useMemo(() => {
    const raw = data?.equipos || []
    const text = query.trim().toLowerCase()
    return raw
      .filter((item) => !text || item.equipo.toLowerCase().includes(text))
      .slice()
      .sort((a, b) => {
        const severity = (SEVERITY[a.semaforo] ?? 9) - (SEVERITY[b.semaforo] ?? 9)
        if (severity !== 0) return severity
        const ah = a.horas_hasta_critico ?? Number.POSITIVE_INFINITY
        const bh = b.horas_hasta_critico ?? Number.POSITIVE_INFINITY
        return ah - bh
      })
  }, [data, query])

  return (
    <aside className="w-full md:w-80 shrink-0 border-b md:border-b-0 md:border-r border-outline-variant/50 bg-surface-container-lowest">
      <div className="sticky top-0 z-10 border-b border-outline-variant/50 bg-surface-container-lowest p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-on-surface">Equipos</h2>
            <p className="font-mono text-[11px] text-on-surface-variant">
              {data ? `${data.total_equipos} unidades` : 'Cargando'}
            </p>
          </div>
          <Truck size={18} className="text-on-surface-variant" />
        </div>
        <label className="flex items-center gap-2 rounded-lg border border-outline-variant/60 bg-surface px-3 py-2">
          <Search size={15} className="text-on-surface-variant" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-sm text-on-surface outline-none"
            placeholder="Buscar equipo"
          />
        </label>
      </div>

      <div className="max-h-[260px] overflow-y-auto p-2 md:max-h-[calc(100vh-150px)]">
        {err && (
          <div className="rounded-lg bg-error/10 p-3 text-sm text-error">{err}</div>
        )}
        {!data && !err && (
          <div className="space-y-2 p-2">
            {[1, 2, 3, 4, 5].map((item) => (
              <div key={item} className="h-14 animate-pulse rounded-lg bg-surface-container-low" />
            ))}
          </div>
        )}
        {equipos.map((equipo) => (
          <EquipoRailItem key={equipo.equipo} equipo={equipo} active={equipo.equipo === activeId} />
        ))}
      </div>
    </aside>
  )
}

function EquipoRailItem({ equipo, active }) {
  const sem = temaSemaforo(equipo.semaforo)
  return (
    <NavLink
      to={`/equipo/${equipo.equipo}`}
      className={`mb-1 flex items-center gap-3 rounded-lg px-3 py-2 transition-colors ${
        active ? 'bg-surface-container-highest' : 'hover:bg-surface-container-low'
      }`}
    >
      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${sem.dot}`} />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-mono text-sm font-bold text-on-surface">
          {equipo.equipo}
        </span>
        <span className="block truncate text-[11px] text-on-surface-variant">
          {equipo.estado_modelo} · {fmtHorasAceite(equipo.horas_actuales)}
        </span>
      </span>
      <span className={`font-mono text-[11px] font-bold ${sem.label_fg}`}>
        {equipo.horas_hasta_critico != null ? `${equipo.horas_hasta_critico.toFixed(0)}h` : 'NA'}
      </span>
    </NavLink>
  )
}
