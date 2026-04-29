import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { MSIcon } from '../components/Layout.jsx'
import { temaSemaforo } from '../semaforo_theme.js'

/**
 * Las 12 variables del backend agrupadas como el diseño (Metales / Contaminantes / Fluido).
 * El orden y los nombres EXACTOS vienen de VARIABLES_ANALITICAS en settings.py.
 */
const GRUPOS = [
  {
    titulo: 'Metales de Desgaste',
    items: [
      { v: 'Fierro ppm',    abbr: 'Fe',  unidad: 'ppm' },
      { v: 'Cobre ppm',     abbr: 'Cu',  unidad: 'ppm' },
      { v: 'Cromo ppm',     abbr: 'Cr',  unidad: 'ppm', bajaConfianza: true },
      { v: 'Aluminio ppm',  abbr: 'Al',  unidad: 'ppm' },
    ],
  },
  {
    titulo: 'Contaminantes',
    items: [
      { v: 'Silicio ppm',   abbr: 'Si', unidad: 'ppm' },
      { v: 'Potasio ppm',   abbr: 'K',  unidad: 'ppm', bajaConfianza: true },
    ],
  },
  {
    titulo: 'Condición del Fluido',
    items: [
      { v: 'Viscosidad a 100 °C cSt', abbr: 'Visc. 100°C', unidad: 'cSt' },
      { v: 'TBN (mg KOH/g)',          abbr: 'TBN',         unidad: 'mgKOH/g' },
      { v: 'Hollin ABS/01 mm',        abbr: 'Hollín',      unidad: 'ABS/01mm' },
      { v: 'Oxidación ABS/01 mm',     abbr: 'Oxidación',   unidad: 'ABS/01mm' },
      { v: 'Sulfatación ABS/01 mm',   abbr: 'Sulfatación', unidad: 'ABS/01mm' },
      { v: 'Nitración ABS/01 mm',     abbr: 'Nitración',   unidad: 'ABS/01mm' },
    ],
  },
]

export default function NuevaMuestra() {
  const { id: equipoFromUrl } = useParams()
  const navigate = useNavigate()

  const [equipos, setEquipos] = useState([])
  const [equipoSel, setEquipoSel] = useState(equipoFromUrl || '')
  const [form, setForm] = useState({
    fecha: new Date().toISOString().slice(0, 10),
    hora_producto: '',
    estado: '',
    lab_id: '',
  })
  const [valores, setValores] = useState({})
  const [result, setResult] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.listarEquipos()
      .then((r) => {
        setEquipos(r.equipos)
        if (!equipoSel && r.equipos.length > 0) setEquipoSel(r.equipos[0])
      })
      .catch((e) => setErr(e.message))
  }, [])

  function setValor(variable, raw) {
    setValores((prev) => ({ ...prev, [variable]: raw }))
  }

  async function submit(e) {
    e.preventDefault()
    setErr(null); setResult(null); setLoading(true)
    try {
      if (!equipoSel) throw new Error('Debes seleccionar un equipo')
      const hora = parseFloat(form.hora_producto)
      if (!Number.isFinite(hora) || hora <= 0) throw new Error('Horas del aceite debe ser > 0')

      const parsed = {}
      for (const g of GRUPOS) {
        for (const it of g.items) {
          const raw = valores[it.v]
          const n = parseFloat(raw)
          if (!Number.isFinite(n) || n < 0) {
            throw new Error(`Falta un valor válido para ${it.v}`)
          }
          parsed[it.v] = n
        }
      }

      const body = {
        fecha: form.fecha,
        hora_producto: hora,
        valores: parsed,
      }
      if (form.estado) body.estado = form.estado

      const res = await api.registrarMuestra(equipoSel, body)
      setResult(res)
      // scroll al resultado
      setTimeout(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }), 100)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="p-6 md:p-12 lg:p-16">
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-12">
        <div className="flex flex-wrap items-center gap-3 mb-2 text-secondary text-sm font-medium tracking-wide">
          <span className="font-mono">{equipoSel || '—'}</span>
          <span className="w-1.5 h-1.5 rounded-full bg-secondary-fixed-dim" />
          <span>Haul Truck · Cat 794AC</span>
          <span className="w-1.5 h-1.5 rounded-full bg-secondary-fixed-dim" />
          <span>Engine Oil</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight text-primary-container mb-4">
          Registro de Muestra
        </h1>
        <p className="text-secondary max-w-2xl text-base md:text-lg">
          Ingrese los parámetros de telemetría y los 12 resultados de laboratorio.
          El sistema guarda la muestra y genera la predicción en el mismo paso.
        </p>
      </div>

      <div className="max-w-4xl mx-auto">
        <form className="space-y-12" onSubmit={submit}>

          {/* ---- 1. Metadatos ---- */}
          <section className="bg-surface-container-lowest p-8 rounded-xl shadow-ambient relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-container to-secondary-fixed-dim opacity-50" />
            <h2 className="text-xs uppercase tracking-[0.05em] font-bold text-secondary mb-8">
              1. Metadatos de operación
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              <div>
                <label className="block text-sm font-medium text-on-surface-variant mb-2">Equipo</label>
                <div className="relative">
                  <select
                    required
                    value={equipoSel}
                    onChange={(e) => setEquipoSel(e.target.value)}
                    className="w-full bg-surface-container-highest font-mono text-on-background px-4 py-3 rounded focus:outline focus:outline-1 focus:outline-primary/20 focus:bg-surface-container-lowest transition-colors text-sm appearance-none pr-10"
                  >
                    {equipos.map((e) => <option key={e} value={e}>{e}</option>)}
                  </select>
                  <MSIcon name="expand_more" className="absolute right-3 top-3 pointer-events-none text-on-surface-variant" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-on-surface-variant mb-2">Fecha de muestreo</label>
                <input
                  required
                  type="date"
                  value={form.fecha}
                  onChange={(e) => setForm({ ...form, fecha: e.target.value })}
                  className="w-full bg-surface-container-highest font-mono text-on-background px-4 py-3 rounded focus:outline focus:outline-1 focus:outline-primary/20 focus:bg-surface-container-lowest transition-colors text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-on-surface-variant mb-2">Horas del aceite</label>
                <div className="relative">
                  <input
                    required
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="Ej: 250"
                    value={form.hora_producto}
                    onChange={(e) => setForm({ ...form, hora_producto: e.target.value })}
                    className="w-full bg-surface-container-highest font-mono text-on-background px-4 py-3 rounded focus:outline focus:outline-1 focus:outline-primary/20 focus:bg-surface-container-lowest transition-colors text-sm pr-12"
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-secondary text-xs font-mono">hrs</span>
                </div>
              </div>

              <div className="md:col-span-2 lg:col-span-2">
                <label className="block text-sm font-medium text-on-surface-variant mb-2">
                  ID de muestra (laboratorio) <span className="opacity-60 font-normal">— opcional</span>
                </label>
                <input
                  type="text"
                  placeholder="LAB-2024-XXXX"
                  value={form.lab_id}
                  onChange={(e) => setForm({ ...form, lab_id: e.target.value })}
                  className="w-full bg-surface-container-highest font-mono text-on-background px-4 py-3 rounded focus:outline focus:outline-1 focus:outline-primary/20 focus:bg-surface-container-lowest transition-colors text-sm"
                />
              </div>
            </div>
          </section>

          {/* ---- 2. Estado ---- */}
          <section className="bg-surface-container-lowest p-8 rounded-xl shadow-ambient">
            <h2 className="text-xs uppercase tracking-[0.05em] font-bold text-secondary mb-8">
              2. Estado declarado <span className="opacity-60">— opcional</span>
            </h2>
            <p className="text-sm font-medium text-on-surface-variant mb-4">
              Si el laboratorio ya clasificó la muestra, indícalo. Si no, el modelo lo predice.
            </p>
            <div className="flex flex-wrap gap-3">
              {['NORMAL', 'PRECAUCION', 'CRITICO'].map((st) => {
                const sem = st === 'CRITICO' ? 'ROJO' : st === 'PRECAUCION' ? 'AMARILLO' : 'VERDE'
                const t = temaSemaforo(sem)
                const active = form.estado === st
                return (
                  <button
                    type="button"
                    key={st}
                    onClick={() => setForm({ ...form, estado: active ? '' : st })}
                    className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                      active ? `${t.chipBg} ring-2 ring-primary-container/30` : 'bg-surface-container-high hover:bg-surface-container-highest'
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${t.dot}`} />
                    <span className={`font-mono text-xs font-bold uppercase tracking-wider ${active ? t.chipFg : 'text-on-surface'}`}>
                      {st}
                    </span>
                  </button>
                )
              })}
              {form.estado && (
                <button
                  type="button"
                  onClick={() => setForm({ ...form, estado: '' })}
                  className="text-xs text-secondary hover:text-primary underline"
                >
                  Limpiar
                </button>
              )}
            </div>
          </section>

          {/* ---- 3. Resultados analíticos ---- */}
          <section className="bg-surface-container-lowest p-8 rounded-xl shadow-ambient">
            <div className="flex justify-between items-end mb-8 pb-4">
              <h2 className="text-xs uppercase tracking-[0.05em] font-bold text-secondary">
                3. Resultados analíticos
              </h2>
              <span className="text-xs font-mono text-secondary">12 variables · requeridas</span>
            </div>

            {GRUPOS.map((g) => (
              <div key={g.titulo} className="mb-10 last:mb-0">
                <h3 className="text-sm font-semibold text-primary-container mb-6 flex items-center">
                  <span className="w-1 h-4 bg-tertiary-fixed-dim mr-2 inline-block rounded-sm" />
                  {g.titulo}
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6">
                  {g.items.map((it) => (
                    <div key={it.v}>
                      <label className="flex justify-between text-xs font-medium text-on-surface-variant mb-1 gap-2">
                        <span className="truncate flex items-center gap-1" title={it.v}>
                          {it.abbr}
                          {it.bajaConfianza && (
                            <MSIcon
                              name="warning"
                              filled
                              className="text-tertiary-fixed-dim"
                              style={{ fontSize: '12px' }}
                            />
                          )}
                        </span>
                        <span className="text-[10px] text-secondary font-mono">{it.unidad}</span>
                      </label>
                      <input
                        required
                        type="number"
                        step="0.01"
                        min="0"
                        value={valores[it.v] ?? ''}
                        onChange={(e) => setValor(it.v, e.target.value)}
                        className="w-full bg-surface-container-highest font-mono text-on-background px-3 py-2 rounded focus:outline focus:outline-1 focus:outline-primary/20 focus:bg-surface-container-lowest transition-colors text-sm text-right"
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </section>

          {/* ---- Errores ---- */}
          {err && (
            <div className="bg-error-container rounded-xl p-4 flex items-start gap-3 text-on-error-container">
              <MSIcon name="error" filled />
              <div className="text-sm">{err}</div>
            </div>
          )}

          {/* ---- CTA ---- */}
          <div className="flex justify-end items-center gap-4 pt-6 pb-12">
            {equipoSel && (
              <Link
                to={`/equipo/${equipoSel}`}
                className="text-on-surface-variant hover:text-primary transition-colors px-4 py-3 text-sm font-medium"
              >
                Cancelar
              </Link>
            )}
            <button
              type="submit"
              disabled={loading}
              className="gradient-primary text-on-primary px-8 py-4 rounded-xl font-medium tracking-wide shadow-ambient hover:opacity-90 transition-opacity disabled:opacity-60 flex items-center gap-3"
            >
              <span>{loading ? 'Procesando…' : 'Guardar y predecir'}</span>
              <MSIcon name={loading ? 'autorenew' : 'memory'} className="text-sm" />
            </button>
          </div>
        </form>

        {/* ---- Resultado ---- */}
        {result && <ResultadoPrediccion pred={result} equipoId={equipoSel} onVerDetalle={() => navigate(`/equipo/${equipoSel}`)} />}
      </div>
    </section>
  )
}

// ==================================================================
// Tarjeta con el resultado de la predicción inmediata
// ==================================================================
function ResultadoPrediccion({ pred, equipoId, onVerDetalle }) {
  const sem = temaSemaforo(pred.semaforo)
  return (
    <section className="bg-surface-container-lowest rounded-xl shadow-ambient p-8 mt-8 space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <div className={`w-14 h-14 rounded-xl ${sem.iconBg} flex items-center justify-center`}>
            <div className={`w-4 h-4 rounded-full ${sem.dot} ${sem.dotGlow}`} />
          </div>
          <div>
            <div className="text-xs font-mono uppercase tracking-widest text-secondary">Predicción · {equipoId}</div>
            <div className="text-3xl font-semibold text-on-background">{pred.estado_modelo}</div>
            <div className={`text-sm font-mono ${sem.label_fg} uppercase tracking-wider mt-1`}>
              Semáforo · {pred.semaforo}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onVerDetalle}
          className="bg-primary-container text-on-primary px-5 py-2.5 rounded-xl font-medium text-sm hover:opacity-90 transition-opacity shadow-ambient"
        >
          Ver detalle del equipo
        </button>
      </div>

      {/* Advertencias de confianza */}
      {pred.advertencias?.length > 0 && (
        <div className="bg-tertiary-fixed/30 rounded-lg p-4 flex items-start gap-3">
          <MSIcon name="warning" className="text-tertiary-container mt-0.5" />
          <ul className="space-y-1 text-sm text-on-tertiary-container">
            {pred.advertencias.map((a, i) => <li key={i}>{a}</li>)}
          </ul>
        </div>
      )}

      {/* KPIs rápidos */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div className="bg-surface-container-low rounded-lg p-4">
          <div className="text-[10px] uppercase tracking-widest text-on-surface-variant font-mono">Horas actuales</div>
          <div className="text-2xl font-mono font-bold text-on-background mt-1">{pred.horas_actuales?.toFixed(1)} h</div>
        </div>
        <div className="bg-surface-container-low rounded-lg p-4">
          <div className="text-[10px] uppercase tracking-widest text-on-surface-variant font-mono flex items-center gap-1">
            Hasta crítico
            {!pred.horas_htc_confiable && pred.horas_hasta_critico != null && (
              <MSIcon name="warning" filled className="text-tertiary-fixed-dim" style={{ fontSize: '12px' }} />
            )}
          </div>
          <div className={`text-2xl font-mono font-bold mt-1 ${sem.label_fg}`}>
            {pred.horas_hasta_critico != null
              ? `${!pred.horas_htc_confiable ? '~' : ''}${pred.horas_hasta_critico.toFixed(1)} h`
              : '—'}
          </div>
        </div>
        <div className="bg-surface-container-low rounded-lg p-4">
          <div className="text-[10px] uppercase tracking-widest text-on-surface-variant font-mono">Última muestra</div>
          <div className="text-2xl font-mono font-bold text-on-background mt-1">{pred.ultima_muestra_fecha || '—'}</div>
        </div>
      </div>

      {/* Predicciones t+1 */}
      <div>
        <div className="text-xs font-mono uppercase tracking-widest text-secondary mb-3">
          Predicciones para t+1
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          {Object.entries(pred.predicciones_t1).map(([v, val]) => {
            const baja = pred.variables_baja_confianza.includes(v)
            return (
              <div key={v} className="bg-surface-container-low rounded-lg px-3 py-2">
                <div className="flex items-center gap-1 text-[11px] text-on-surface-variant truncate" title={v}>
                  {v}
                  {baja && <MSIcon name="warning" filled className="text-tertiary-fixed-dim" style={{ fontSize: '12px' }} />}
                </div>
                <div className="font-mono text-on-surface font-semibold">{val.toFixed(2)}</div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
