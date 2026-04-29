import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../api.js'
import { MSIcon } from '../components/Layout.jsx'
import { temaSemaforo, fmtHoras, fmtHorasAceite } from '../semaforo_theme.js'

const COLOR_ESTADO = { NORMAL: '#565e74', PRECAUCION: '#dec29a', CRITICO: '#ba1a1a' }

export default function Equipo() {
  const { id } = useParams()
  const [pred, setPred]   = useState(null)
  const [histo, setHisto] = useState(null)
  const [meta, setMeta]   = useState(null)
  const [varSel, setVarSel] = useState(null)
  const [err, setErr]     = useState(null)

  useEffect(() => {
    setPred(null); setHisto(null); setMeta(null); setErr(null)
    Promise.all([api.prediccion(id), api.historial(id), api.variables()])
      .then(([p, h, m]) => {
        setPred(p); setHisto(h); setMeta(m)
        setVarSel(m.variables?.[0] || null)
      })
      .catch((e) => setErr(e.message))
  }, [id])

  const limitesMap = useMemo(() => {
    if (!meta) return {}
    const map = {}
    for (const l of meta.limites) map[l.variable] = l
    return map
  }, [meta])

  const chartData = useMemo(() => {
    if (!histo || !varSel) return []
    return histo.historial
      .slice()
      .sort((a, b) => a.hora_producto - b.hora_producto)
      .map((h) => ({
        hora: h.hora_producto,
        valor: h.valores[varSel] ?? null,
        estado: h.estado || 'NORMAL',
      }))
      .filter((r) => r.valor != null)
  }, [histo, varSel])

  const predVal  = varSel ? pred?.predicciones_t1?.[varSel] : null
  const horaPred = pred?.horas_actuales ? pred.horas_actuales + 80 : null

  if (err) return (
    <section className="p-6 md:p-10">
      <div className="bg-error-container rounded-xl p-6 text-on-error-container">Error: {err}</div>
    </section>
  )
  if (!pred || !histo || !meta) return (
    <section className="p-6 md:p-10"><div className="bg-surface-container-low rounded-xl p-10 animate-pulse h-96" /></section>
  )

  const sem = temaSemaforo(pred.semaforo)
  const ultimoValor = histo.historial[0]?.valores

  return (
    <section className="p-6 md:p-10 lg:p-12">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Breadcrumb */}
        <nav aria-label="Migas de pan" className="flex text-sm text-on-surface-variant font-medium tracking-wide">
          <ol className="inline-flex items-center gap-1 md:gap-3">
            <li className="inline-flex items-center">
              <Link to="/" className="hover:text-primary transition-colors">Flota</Link>
            </li>
            <li className="flex items-center">
              <MSIcon name="chevron_right" className="text-sm mx-1 opacity-50" />
              <span className="text-on-background font-semibold">{pred.equipo}</span>
            </li>
          </ol>
        </nav>

        {/* Hero */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex flex-wrap items-center gap-4 mb-2">
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-on-background">
                {pred.equipo}
              </h1>
              <div className={`flex items-center gap-2 ${sem.chipBg} px-3 py-1.5 rounded-lg`}>
                <div className={`w-2 h-2 rounded-full ${sem.dot}`} />
                <span className={`font-mono text-xs font-bold ${sem.chipFg} uppercase tracking-wider`}>
                  {pred.estado_modelo}
                </span>
              </div>
              <span className="text-xs font-mono text-on-surface-variant uppercase tracking-widest">
                Semáforo · {pred.semaforo}
              </span>
            </div>
            <p className="text-on-surface-variant text-sm max-w-2xl mt-4 leading-relaxed">
              Haul Truck · Caterpillar 794AC · Engine Oil Compartment · Quellaveco
            </p>
          </div>
          <Link
            to={`/nueva-muestra/${pred.equipo}`}
            className="bg-primary-container text-on-primary px-6 py-3 rounded-xl font-medium text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity shadow-ambient shrink-0"
          >
            <MSIcon name="add" className="text-sm" />
            Registrar nueva muestra
          </Link>
        </div>

        {/* Advertencias de confianza */}
        {pred.advertencias?.length > 0 && (
          <div className="bg-tertiary-fixed/30 rounded-xl p-4 flex items-start gap-4">
            <MSIcon name="warning" className="text-tertiary-container mt-0.5" />
            <div>
              <h4 className="text-on-tertiary-container font-semibold text-sm mb-1">
                Advertencias de confianza
              </h4>
              <ul className="space-y-1">
                {pred.advertencias.map((a, i) => (
                  <li key={i} className="text-on-tertiary-container/80 text-sm">{a}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* KPI strip */}
        <div className="bg-surface-container-low rounded-xl p-2 grid grid-cols-2 md:grid-cols-4 gap-2">
          <div className="bg-surface-container-lowest p-6 rounded-lg flex flex-col justify-between">
            <span className="text-xs uppercase tracking-widest text-on-surface-variant font-medium mb-4">
              Horas actuales
            </span>
            <span className="font-mono text-3xl font-bold text-on-background">
              {fmtHoras(pred.horas_actuales)}
              <span className="text-sm font-sans text-on-surface-variant ml-1 font-normal">hrs</span>
            </span>
          </div>

          <div className="bg-surface-container-lowest p-6 rounded-lg flex flex-col justify-between relative overflow-hidden">
            <div className={`absolute top-0 right-0 w-1 h-full ${sem.barra} rounded-full`} />
            <span className="text-xs uppercase tracking-widest text-on-surface-variant font-medium mb-4 flex items-center gap-1">
              Hasta crítico
              {!pred.horas_htc_confiable && pred.horas_hasta_critico != null && (
                <MSIcon name="warning" filled className={`text-sm ${sem.iconFg}`} />
              )}
            </span>
            <span className={`font-mono text-3xl font-bold ${sem.label_fg}`}>
              {pred.horas_hasta_critico != null
                ? <>{!pred.horas_htc_confiable && '~'}{pred.horas_hasta_critico.toFixed(1)}
                    <span className="text-sm font-sans opacity-70 ml-1 font-normal">hrs</span></>
                : '—'}
            </span>
          </div>

          <div className="bg-surface-container-lowest p-6 rounded-lg flex flex-col justify-between">
            <span className="text-xs uppercase tracking-widest text-on-surface-variant font-medium mb-4 flex items-center gap-1">
              Total muestras
              {!pred.historia_suficiente && <MSIcon name="warning" filled className="text-sm text-tertiary-fixed-dim" />}
            </span>
            <span className="font-mono text-3xl font-bold text-on-background">
              {String(histo.total_muestras).padStart(2, '0')}
            </span>
          </div>

          <div className="bg-surface-container-lowest p-6 rounded-lg flex flex-col justify-between">
            <span className="text-xs uppercase tracking-widest text-on-surface-variant font-medium mb-4">
              Última muestra
            </span>
            <span className="font-mono text-lg font-bold text-on-background">
              {pred.ultima_muestra_fecha || '—'}
            </span>
          </div>
        </div>

        {/* Curva de degradación */}
        <section className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div>
              <h2 className="text-lg font-headline font-semibold text-on-surface">
                Curva de degradación
              </h2>
              <p className="text-xs text-on-surface-variant mt-1">
                Eje X: Hora_Producto (horas acumuladas del aceite). ★ = predicción t+1.
              </p>
            </div>
            <select
              value={varSel || ''}
              onChange={(e) => setVarSel(e.target.value)}
              className="bg-surface-container-high rounded-lg px-3 py-2 text-sm font-mono text-on-surface focus:outline focus:outline-1 focus:outline-primary/20"
            >
              {meta.variables.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 10 }}>
                <CartesianGrid stroke="#e0e3e5" strokeDasharray="3 3" />
                <XAxis
                  dataKey="hora" stroke="#5c5e68" type="number" domain={['dataMin', 'dataMax']}
                  label={{ value: 'Hora_Producto (h)', position: 'insideBottom', offset: -4, fill: '#5c5e68', fontSize: 11 }}
                />
                <YAxis stroke="#5c5e68" />
                <Tooltip
                  contentStyle={{ background: '#ffffff', border: '1px solid #c6c6cd', borderRadius: 8, fontFamily: 'JetBrains Mono' }}
                  labelStyle={{ color: '#191c1e' }}
                />
                <Line
                  type="monotone" dataKey="valor" name={varSel}
                  stroke="#131b2e" strokeWidth={2} isAnimationActive={false}
                  dot={({ payload, cx, cy }) => (
                    <circle cx={cx} cy={cy} r={4}
                            fill={COLOR_ESTADO[payload.estado] || '#131b2e'}
                            stroke="#ffffff" strokeWidth={1} />
                  )}
                />
                {predVal != null && horaPred != null && (
                  <ReferenceDot x={horaPred} y={predVal} r={10}
                                fill="#dec29a" stroke="#131b2e" strokeWidth={2}
                                label={{ value: '★', position: 'center', fill: '#131b2e', fontSize: 14, fontWeight: 800 }} />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Gauges — última muestra */}
        <section>
          <h2 className="text-lg font-headline font-semibold text-on-surface mb-4">
            Última muestra · valores actuales
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {meta.variables.map((v) => (
              <Gauge
                key={v}
                variable={v}
                valor={ultimoValor?.[v]}
                limites={limitesMap[v]}
                bajaConfianza={meta.baja_confianza.includes(v)}
              />
            ))}
          </div>
        </section>

        {/* Predicciones t+1 */}
        <section>
          <h2 className="text-lg font-headline font-semibold text-on-surface mb-4">
            Predicciones para la próxima muestra (t+1)
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(pred.predicciones_t1).map(([v, val]) => (
              <Gauge
                key={v}
                variable={v}
                valor={val}
                limites={limitesMap[v]}
                bajaConfianza={pred.variables_baja_confianza.includes(v)}
              />
            ))}
          </div>
        </section>

        {/* Historial */}
        <section className="bg-surface-container-lowest rounded-xl shadow-ambient overflow-hidden">
          <div className="px-5 py-4 border-b border-outline-variant/40">
            <h2 className="text-lg font-headline font-semibold text-on-surface">
              Historial completo ({histo.total_muestras} muestras)
            </h2>
          </div>
          <div className="overflow-auto max-h-[420px]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface-container text-xs uppercase tracking-wider text-on-surface-variant">
                <tr>
                  <th className="px-4 py-2 text-left">Fecha</th>
                  <th className="px-4 py-2 text-right">Hora_Producto</th>
                  <th className="px-4 py-2 text-left">Estado</th>
                  {meta.variables.slice(0, 6).map((v) => (
                    <th key={v} className="px-3 py-2 text-right whitespace-nowrap">{v}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {histo.historial.map((m, i) => {
                  const estadoSem = m.estado === 'CRITICO' ? 'ROJO'
                                   : m.estado === 'PRECAUCION' ? 'AMARILLO'
                                   : 'VERDE'
                  const s = temaSemaforo(estadoSem)
                  return (
                    <tr key={i} className="border-t border-outline-variant/30 hover:bg-surface-container-low/50">
                      <td className="px-4 py-2 font-mono">{m.fecha || '—'}</td>
                      <td className="px-4 py-2 text-right font-mono">{m.hora_producto?.toFixed(1)}</td>
                      <td className="px-4 py-2">
                        <span className={`inline-flex items-center gap-1.5 ${s.chipBg} px-2 py-0.5 rounded`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                          <span className={`font-mono text-[10px] font-bold uppercase tracking-wider ${s.chipFg}`}>
                            {m.estado || '—'}
                          </span>
                        </span>
                      </td>
                      {meta.variables.slice(0, 6).map((v) => (
                        <td key={v} className="px-3 py-2 text-right font-mono text-on-surface">
                          {m.valores[v] != null ? m.valores[v].toFixed(2) : '—'}
                        </td>
                      ))}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  )
}

// ====================================================================
// Gauge individual — colorea el valor según LIMITES_ALERTA del backend
// ====================================================================
function Gauge({ variable, valor, limites, bajaConfianza }) {
  let color = 'text-on-surface'
  if (limites && valor != null) {
    const { direccion, verde_min, verde_max, amarillo_min, amarillo_max } = limites
    if (direccion === 'mayor') {
      if (valor <= (limites.verde_max ?? Infinity)) color = 'text-surface-tint'
      else if (valor <= (limites.amarillo_max ?? Infinity)) color = 'text-on-tertiary-container'
      else color = 'text-error'
    } else if (direccion === 'menor') {
      if (valor >= (verde_min ?? -Infinity)) color = 'text-surface-tint'
      else if (valor >= (amarillo_min ?? -Infinity)) color = 'text-on-tertiary-container'
      else color = 'text-error'
    } else if (direccion === 'rango') {
      if (valor >= (verde_min ?? -Infinity) && valor <= (verde_max ?? Infinity)) color = 'text-surface-tint'
      else if (valor >= (amarillo_min ?? -Infinity) && valor <= (amarillo_max ?? Infinity)) color = 'text-on-tertiary-container'
      else color = 'text-error'
    }
  }
  return (
    <div className="bg-surface-container-lowest rounded-lg p-4 shadow-ambient">
      <div className="flex items-center justify-between gap-2">
        <div
          className="text-[11px] uppercase tracking-wider text-on-surface-variant truncate font-headline"
          title={variable}
        >
          {variable}
        </div>
        {bajaConfianza && (
          <MSIcon
            name="warning"
            filled
            className="text-tertiary-fixed-dim text-sm shrink-0"
            style={{ fontSize: '14px' }}
          />
        )}
      </div>
      <div className={`mt-2 text-2xl font-mono font-bold ${color}`}>
        {valor != null ? Number(valor).toFixed(2) : '—'}
      </div>
    </div>
  )
}
