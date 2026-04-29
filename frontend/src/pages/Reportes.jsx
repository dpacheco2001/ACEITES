import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { MSIcon } from '../components/Layout.jsx'

export default function Reportes() {
  const [equipos, setEquipos] = useState([])
  const [equipoSel, setEquipoSel] = useState('')
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')
  const [formatoEquipo, setFormatoEquipo] = useState('excel')
  const [formatoFlota, setFormatoFlota]   = useState('excel')

  const [loadingEquipo, setLoadingEquipo] = useState(false)
  const [loadingFlota, setLoadingFlota]   = useState(false)
  const [msg, setMsg] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.listarEquipos()
      .then((r) => { setEquipos(r.equipos); setEquipoSel(r.equipos[0] || '') })
      .catch((e) => setErr(e.message))
  }, [])

  async function descargar(label, doFetch, filename) {
    setMsg(null); setErr(null)
    try {
      const res = await doFetch()
      if (!res.ok) throw new Error(`Error descargando ${label}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
      setMsg(`Descargado: ${filename}`)
    } catch (e) {
      setErr(e.message)
    }
  }

  async function descargarEquipo() {
    if (!equipoSel) { setErr('Selecciona un equipo'); return }
    setLoadingEquipo(true)
    const ext = formatoEquipo === 'csv' ? 'csv' : 'xlsx'
    const rango = (fechaDesde || fechaHasta) ? `_${fechaDesde || 'inicio'}_a_${fechaHasta || 'hoy'}` : ''
    await descargar(
      'historial',
      () => api.exportar(equipoSel, formatoEquipo, fechaDesde, fechaHasta),
      `${equipoSel}_historial${rango}.${ext}`,
    )
    setLoadingEquipo(false)
  }

  async function descargarFlota() {
    setLoadingFlota(true)
    const ext = formatoFlota === 'csv' ? 'csv' : 'xlsx'
    const hoy = new Date().toISOString().slice(0, 10)
    await descargar(
      'resumen de flota',
      () => api.exportarFlota(formatoFlota),
      `flota_resumen_${hoy}.${ext}`,
    )
    setLoadingFlota(false)
  }

  return (
    <section>
      <div className="pt-8 pb-6 px-6 lg:px-12 max-w-7xl mx-auto w-full">
        <h2 className="text-4xl font-headline font-semibold text-on-background tracking-tight">
          Reportes de rendimiento
        </h2>
        <p className="font-mono text-sm text-on-surface-variant mt-2 tracking-wide">
          GENERACIÓN DE DATOS EXPORTABLES
        </p>
      </div>

      <div className="px-6 lg:px-12 pb-24 max-w-7xl mx-auto w-full flex flex-col gap-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* ---- Card A: Historial por equipo ---- */}
          <div className="bg-surface-container-lowest rounded-xl p-8 flex flex-col gap-6 shadow-ambient h-full">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-headline font-semibold text-xl text-on-background">
                  Historial por equipo
                </h3>
                <p className="font-body text-sm text-on-surface-variant mt-1">
                  Análisis detallado de rendimiento individual en el rango seleccionado.
                </p>
              </div>
              <MSIcon
                name="history"
                className="text-outline-variant shrink-0"
                style={{ fontVariationSettings: "'wght' 200, 'FILL' 0", fontSize: '28px' }}
              />
            </div>

            <div className="flex flex-col gap-4 mt-2 flex-1">
              <div className="flex flex-col gap-2">
                <label className="font-label text-xs uppercase tracking-[0.05em] text-on-surface-variant">
                  Seleccionar equipo
                </label>
                <div className="relative">
                  <select
                    value={equipoSel}
                    onChange={(e) => setEquipoSel(e.target.value)}
                    className="w-full bg-surface-container-high rounded-sm px-4 py-3 font-mono text-sm text-on-surface focus:outline focus:outline-1 focus:outline-primary/20 appearance-none"
                  >
                    {equipos.map((e) => <option key={e} value={e}>{e}</option>)}
                  </select>
                  <MSIcon name="expand_more" className="absolute right-3 top-3 pointer-events-none text-on-surface-variant" />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label className="font-label text-xs uppercase tracking-[0.05em] text-on-surface-variant">
                  Rango de fechas <span className="opacity-60 normal-case tracking-normal">(opcional)</span>
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <input
                    type="date"
                    value={fechaDesde}
                    onChange={(e) => setFechaDesde(e.target.value)}
                    className="w-full bg-surface-container-high rounded-sm px-4 py-3 font-mono text-sm text-on-surface focus:outline focus:outline-1 focus:outline-primary/20"
                  />
                  <input
                    type="date"
                    value={fechaHasta}
                    onChange={(e) => setFechaHasta(e.target.value)}
                    className="w-full bg-surface-container-high rounded-sm px-4 py-3 font-mono text-sm text-on-surface focus:outline focus:outline-1 focus:outline-primary/20"
                  />
                </div>
                {(fechaDesde || fechaHasta) && (
                  <button
                    type="button"
                    onClick={() => { setFechaDesde(''); setFechaHasta('') }}
                    className="self-start text-xs text-on-surface-variant hover:text-primary underline"
                  >
                    Limpiar filtro de fechas
                  </button>
                )}
              </div>

              <div className="flex flex-col gap-2">
                <label className="font-label text-xs uppercase tracking-[0.05em] text-on-surface-variant">
                  Formato
                </label>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { val: 'excel', lbl: 'Excel (.xlsx)' },
                    { val: 'csv',   lbl: 'CSV'           },
                  ].map((o) => (
                    <label
                      key={o.val}
                      className="flex items-center gap-3 p-3 bg-surface rounded-sm cursor-pointer hover:bg-surface-container-low transition-colors"
                    >
                      <input
                        type="radio"
                        name="fmt-equipo"
                        className="text-primary-container focus:ring-primary-container"
                        checked={formatoEquipo === o.val}
                        onChange={() => setFormatoEquipo(o.val)}
                      />
                      <span className="font-mono text-sm text-on-surface">{o.lbl}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 mt-4 pt-4">
              <button
                type="button"
                onClick={descargarEquipo}
                disabled={loadingEquipo}
                className="bg-primary-container text-on-primary rounded-xl px-6 py-3 font-headline font-medium text-sm flex items-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                <MSIcon name={loadingEquipo ? 'autorenew' : 'download'} style={{ fontSize: '18px' }} />
                {loadingEquipo ? 'Procesando…' : (formatoEquipo === 'csv' ? 'Exportar CSV' : 'Exportar Excel')}
              </button>
            </div>
          </div>

          {/* ---- Card B: Resumen de flota ---- */}
          <div className="bg-surface-container-lowest rounded-xl p-8 flex flex-col gap-6 shadow-ambient h-full">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-headline font-semibold text-xl text-on-background">
                  Resumen de flota
                </h3>
                <p className="font-body text-sm text-on-surface-variant mt-1">
                  Una fila por equipo con semáforo, horas, hasta crítico y flags de confianza.
                </p>
              </div>
              <MSIcon
                name="dashboard"
                className="text-outline-variant shrink-0"
                style={{ fontVariationSettings: "'wght' 200, 'FILL' 0", fontSize: '28px' }}
              />
            </div>

            <div className="flex flex-col gap-4 mt-2 flex-1">
              <div className="bg-surface-container-low rounded-lg p-4 space-y-2">
                <div className="text-xs font-mono uppercase tracking-widest text-on-surface-variant">
                  Columnas incluidas
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {['Equipo','Semáforo','Estado_modelo','Horas_actuales','Horas_hasta_critico','Última_muestra','Total_muestras','Historia_suficiente','Horas_HTC_confiable'].map((c) => (
                    <span key={c} className="inline-block bg-surface-container-high rounded px-2 py-0.5 text-[10px] font-mono text-on-surface">
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label className="font-label text-xs uppercase tracking-[0.05em] text-on-surface-variant">
                  Formato
                </label>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { val: 'excel', lbl: 'Excel (.xlsx)' },
                    { val: 'csv',   lbl: 'CSV'           },
                  ].map((o) => (
                    <label
                      key={o.val}
                      className="flex items-center gap-3 p-3 bg-surface rounded-sm cursor-pointer hover:bg-surface-container-low transition-colors"
                    >
                      <input
                        type="radio"
                        name="fmt-flota"
                        className="text-primary-container focus:ring-primary-container"
                        checked={formatoFlota === o.val}
                        onChange={() => setFormatoFlota(o.val)}
                      />
                      <span className="font-mono text-sm text-on-surface">{o.lbl}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 mt-4 pt-4">
              <button
                type="button"
                onClick={descargarFlota}
                disabled={loadingFlota}
                className="bg-primary-container text-on-primary rounded-xl px-6 py-3 font-headline font-medium text-sm flex items-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                <MSIcon name={loadingFlota ? 'autorenew' : 'table_chart'} style={{ fontSize: '18px' }} />
                {loadingFlota ? 'Procesando…' : (formatoFlota === 'csv' ? 'Exportar CSV' : 'Exportar Excel')}
              </button>
            </div>
          </div>
        </div>

        {/* ---- Mensaje ---- */}
        {(msg || err) && (
          <div
            className={`rounded-xl p-4 flex items-start gap-3 ${
              err ? 'bg-error-container text-on-error-container' : 'bg-surface-container-highest text-on-surface'
            }`}
          >
            <MSIcon name={err ? 'error' : 'check_circle'} filled />
            <div className="text-sm font-medium">{err || msg}</div>
          </div>
        )}
      </div>
    </section>
  )
}
