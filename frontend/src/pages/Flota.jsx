import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { MSIcon } from '../components/Layout.jsx'
import LoadingProgress from '../components/LoadingProgress.jsx'
import { temaSemaforo, fmtHorasAceite, relativeAgo } from '../semaforo_theme.js'

export default function Flota() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)
  const [filtro, setFiltro] = useState('TODOS')
  const [limit, setLimit] = useState(16)

  useEffect(() => {
    api.resumenFlota()
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  const equiposFiltrados = useMemo(() => {
    if (!data) return []
    if (filtro === 'TODOS') return data.equipos
    return data.equipos.filter((e) => e.semaforo === filtro)
  }, [data, filtro])

  const visibles = equiposFiltrados.slice(0, limit)

  if (loading) {
    return (
      <section className="p-6 md:p-10">
        <LoadingProgress
          active={loading}
          label="Calculando resumen de flota"
          note="Atlas esperara estos resultados antes de explicar el dashboard."
        />
        <div className="mt-6 bg-surface-container-low rounded-xl h-32 animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          {[1,2,3,4].map(i => <div key={i} className="bg-surface-container-low rounded-xl h-32 animate-pulse" />)}
        </div>
      </section>
    )
  }
  if (err) {
    return (
      <section className="p-6 md:p-10">
        <div className="bg-error-container rounded-xl p-6 text-on-error-container">
          Error cargando flota: {err}
        </div>
      </section>
    )
  }
  if (!data) return null

  return (
    <section className="p-6 md:p-10">
      {/* Header */}
      <div className="mb-8 flex flex-col sm:flex-row sm:justify-between sm:items-end gap-4">
        <div>
          <h1 className="text-3xl font-headline font-semibold text-on-surface tracking-tight">
            Estado actual de la flota
          </h1>
          <p className="text-on-surface-variant mt-2 font-body text-sm max-w-2xl">
            Monitoreo en tiempo real de {data.total_equipos} unidades Caterpillar 794AC · Mina Q.
            Prioridad a umbrales de mantenimiento crítico.
          </p>
        </div>
        <div className="hidden sm:flex gap-3">
          <Link
            to="/reportes"
            className="px-4 py-2 bg-surface-container-high text-on-surface rounded-lg font-mono text-xs font-bold uppercase tracking-wider hover:bg-surface-container-highest transition-colors flex items-center"
          >
            <MSIcon name="download" className="text-sm mr-2" />
            Export Log
          </Link>
          <Link
            to="/nueva-muestra"
            className="px-5 py-2 gradient-primary text-on-primary rounded-xl font-headline font-semibold text-sm hover:opacity-90 transition-opacity flex items-center shadow-ambient"
          >
            <MSIcon name="add_chart" className="text-sm mr-2" />
            Nueva muestra
          </Link>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <KpiCard
          title="Total Unidades"
          value={data.total_equipos}
          unit="ACT"
          icon="local_shipping"
          theme="neutral"
          active={filtro === 'TODOS'}
          onClick={() => setFiltro('TODOS')}
        />
        <KpiCard
          title="Crítico"
          value={data.criticos}
          unit="UNITS"
          icon="warning"
          theme="error"
          active={filtro === 'ROJO'}
          onClick={() => setFiltro('ROJO')}
        />
        <KpiCard
          title="Precaución"
          value={data.precaucion}
          unit="UNITS"
          icon="info"
          theme="tertiary"
          active={filtro === 'AMARILLO'}
          onClick={() => setFiltro('AMARILLO')}
        />
        <KpiCard
          title="Óptimo"
          value={data.normales}
          unit="UNITS"
          icon="check_circle"
          theme="neutral-ok"
          active={filtro === 'VERDE'}
          onClick={() => setFiltro('VERDE')}
        />
      </div>

      {/* Grid de equipos */}
      {visibles.length === 0 ? (
        <div className="bg-surface-container-lowest rounded-xl p-10 text-center text-on-surface-variant shadow-ambient">
          <MSIcon name="local_shipping" className="text-5xl opacity-30" />
          <p className="mt-4 font-headline text-sm">No hay equipos con el filtro seleccionado.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {visibles.map((e) => <EquipoCard key={e.equipo} e={e} />)}
        </div>
      )}

      {/* Load more */}
      {equiposFiltrados.length > limit && (
        <div className="mt-8 flex justify-center pb-8">
          <button
            type="button"
            onClick={() => setLimit((l) => l + 12)}
            className="px-6 py-2 bg-transparent text-on-surface-variant rounded-lg font-mono text-xs font-bold uppercase tracking-wider hover:bg-surface-container-high transition-colors"
          >
            Load More Units ({equiposFiltrados.length - limit} restantes)
          </button>
        </div>
      )}
    </section>
  )
}

// ===================================================================
// KPI card — 4 variantes + toggle de filtro
// ===================================================================
function KpiCard({ title, value, unit, icon, theme, active, onClick }) {
  const themes = {
    'neutral':    { bg: 'bg-surface-container-lowest', fg: 'text-on-surface',            dot: 'bg-surface-tint', labelFg: 'text-on-surface-variant' },
    'error':      { bg: 'bg-error-container',          fg: 'text-on-error-container',    dot: 'bg-error',        labelFg: 'text-on-error-container'  },
    'tertiary':   { bg: 'bg-tertiary-container',       fg: 'text-on-tertiary-container', dot: 'bg-tertiary-fixed-dim', labelFg: 'text-on-tertiary-container' },
    'neutral-ok': { bg: 'bg-surface-container-lowest', fg: 'text-on-surface',            dot: 'bg-surface-tint', labelFg: 'text-on-surface-variant' },
  }
  const t = themes[theme] || themes.neutral
  const padValue = String(value).padStart(2, '0')

  return (
    <button
      type="button"
      onClick={onClick}
      className={`${t.bg} p-5 rounded-xl shadow-ambient flex flex-col justify-between h-32 relative overflow-hidden group text-left transition-all ${
        active ? 'ring-2 ring-primary-container/40' : 'hover:opacity-95'
      }`}
    >
      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        <MSIcon name={icon} className={`text-6xl ${t.fg}`} />
      </div>
      <div className="flex items-center gap-2 relative z-10">
        <div className={`w-2 h-2 rounded-full ${t.dot}`} />
        <span className={`font-headline text-xs tracking-widest uppercase ${t.labelFg}`}>
          {title}
        </span>
      </div>
      <div className="flex items-baseline gap-2 relative z-10">
        <span className={`font-mono text-4xl font-bold ${t.fg}`}>{padValue}</span>
        <span className={`font-mono text-xs ${t.fg} opacity-70`}>{unit}</span>
      </div>
    </button>
  )
}

// ===================================================================
// Tarjeta de equipo
// ===================================================================
function EquipoCard({ e }) {
  const sem = temaSemaforo(e.semaforo)
  const warn = !e.historia_suficiente || !e.horas_htc_confiable
  return (
    <Link
      to={`/equipo/${e.equipo}`}
      className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient flex flex-col gap-4 hover:bg-surface-container-highest transition-colors cursor-pointer group"
    >
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 ${sem.iconBg} rounded-lg flex items-center justify-center`}>
            <MSIcon name="local_shipping" className={`${sem.iconFg} text-xl`} />
          </div>
          <div>
            <h3 className="font-mono font-bold text-lg text-on-surface leading-tight">
              {e.equipo}
            </h3>
            <span className="font-headline text-[10px] uppercase tracking-wider text-on-surface-variant">
              Cat 794AC · Motor
            </span>
          </div>
        </div>
        <div className={`w-2 h-2 rounded-full ${sem.dot} ${sem.dotGlow}`} />
      </div>

      <div className="bg-surface-container-low rounded-lg p-3 space-y-2">
        <div className="flex justify-between items-center">
          <span className="font-body text-xs text-on-surface-variant">Horas Actuales</span>
          <span className="font-mono text-sm font-bold text-on-surface">
            {fmtHorasAceite(e.horas_actuales)}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className={`font-body text-xs ${sem.label_fg} font-semibold`}>
            Hasta Crítico
          </span>
          <div className="flex items-center gap-1">
            {(!e.horas_htc_confiable && e.horas_hasta_critico != null) && (
              <MSIcon
                name="warning"
                filled
                className={`text-[14px] ${sem.iconFg}`}
                style={{ fontSize: '14px' }}
              />
            )}
            <span className={`font-mono text-sm font-bold ${sem.label_fg}`}>
              {e.horas_hasta_critico != null
                ? `${!e.horas_htc_confiable ? '~' : ''}${e.horas_hasta_critico.toFixed(1)}h`
                : '—'}
            </span>
          </div>
        </div>
      </div>

      <div className="flex justify-between items-center mt-auto pt-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-on-surface-variant opacity-60">
            UPD: {relativeAgo(e.ultima_muestra_fecha)}
          </span>
          {!e.historia_suficiente && (
            <span
              className="text-[10px] font-mono text-on-tertiary-container bg-tertiary-fixed/50 px-1.5 py-0.5 rounded"
              title="Historia insuficiente (< 5 muestras)"
            >
              N={e.total_muestras}
            </span>
          )}
        </div>
        <MSIcon name="arrow_forward" className="text-on-surface-variant text-sm group-hover:opacity-70 transition-opacity" />
      </div>
    </Link>
  )
}
