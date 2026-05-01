import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, Database, Download, FileSearch, Table2, UploadCloud } from 'lucide-react'
import { api } from '../api.js'
import LoadingProgress from '../components/LoadingProgress.jsx'

export default function AdminDatos() {
  const [status, setStatus] = useState(null)
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)
  const [validation, setValidation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const required = useMemo(() => status?.required_headers || validation?.required_headers || [], [status, validation])
  const previewColumns = useMemo(() => preview?.columns || [], [preview])

  async function loadStatus() {
    setErr(null)
    setLoading(true)
    try {
      const [nextStatus, nextPreview] = await Promise.all([
        api.datasetStatus(),
        api.datasetPreview(),
      ])
      setStatus(nextStatus)
      setPreview(nextPreview)
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  async function validate() {
    if (!file) return
    setBusy(true)
    setErr(null)
    try {
      setValidation(await api.datasetValidate(file))
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  async function importDataset() {
    if (!file) return
    setBusy(true)
    setErr(null)
    try {
      setStatus(await api.datasetImport(file))
      setPreview(await api.datasetPreview())
      setValidation(null)
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  function downloadDataset() {
    window.location.href = api.datasetDownloadUrl()
  }

  return (
    <div className="min-h-full bg-surface text-on-background">
      <div className="border-b border-outline-variant/40 bg-surface-container-low px-4 md:px-8 py-5">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-on-surface-variant font-mono">
              Organización · {status?.org_name || status?.tenant_key || 'datos'}
            </p>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight mt-1">
              Ingesta de dataset
            </h1>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <Database size={18} />
            {loading ? 'Revisando dataset' : status?.loaded ? `${status.total_rows} filas · ${status.total_equipos} equipos` : 'Sin dataset cargado'}
          </div>
        </div>
      </div>

      {busy && <LoadingProgress label="Procesando archivo y validando estructura" />}

      <div className="max-w-6xl mx-auto p-4 md:p-8 grid lg:grid-cols-[minmax(0,1fr)_360px] gap-6">
        <section className="space-y-5">
          {!loading && !status?.loaded && (
            <div className="rounded-lg border border-warning/40 bg-warning-container/60 p-4 flex gap-3">
              <AlertTriangle className="mt-0.5 shrink-0" size={20} />
              <div>
                <h2 className="font-bold">Carga requerida antes de abrir Flota</h2>
                <p className="text-sm text-on-surface-variant mt-1">
                  Esta organización no tiene dataset operativo. Carga el Excel validado para habilitar dashboard, equipos, reportes y Atlas.
                </p>
              </div>
            </div>
          )}

          <div className="rounded-lg border border-outline-variant/50 bg-surface-container-low p-5 space-y-4">
            <label className="block">
              <span className="block text-xs uppercase tracking-widest text-on-surface-variant mb-2">
                Archivo Excel o CSV
              </span>
              <input
                type="file"
                accept=".xlsx,.xls,.xlsm,.csv"
                className="block w-full text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-primary file:px-4 file:py-2 file:text-on-primary file:font-bold"
                onChange={(e) => {
                  setFile(e.target.files?.[0] || null)
                  setValidation(null)
                }}
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={!file || busy}
                onClick={validate}
                className="inline-flex items-center gap-2 rounded-lg border border-outline-variant px-4 py-2 text-sm font-bold disabled:opacity-50"
              >
                <FileSearch size={16} /> Validar
              </button>
              <button
                type="button"
                disabled={!file || busy || validation?.ok === false}
                onClick={importDataset}
                className="inline-flex items-center gap-2 rounded-lg bg-primary text-on-primary px-4 py-2 text-sm font-bold disabled:opacity-50"
              >
                <UploadCloud size={16} /> Importar dataset
              </button>
            </div>
          </div>

          {preview?.loaded && (
            <div className="rounded-lg border border-outline-variant/50 bg-surface-container-low overflow-hidden">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 px-5 py-4 border-b border-outline-variant/40">
                <div>
                  <div className="flex items-center gap-2 font-bold">
                    <Table2 size={18} />
                    Dataset activo
                  </div>
                  <p className="text-sm text-on-surface-variant mt-1">
                    Vista previa de las primeras filas cargadas para esta organización.
                  </p>
                </div>
                <div className="text-xs uppercase tracking-widest text-on-surface-variant font-mono">
                  {preview.total_rows} filas · {preview.total_equipos} equipos
                </div>
                <button
                  type="button"
                  onClick={downloadDataset}
                  className="inline-flex items-center gap-2 rounded-lg border border-outline-variant px-3 py-2 text-xs font-bold uppercase tracking-wider hover:bg-surface-container-highest"
                >
                  <Download size={15} /> Descargar
                </button>
              </div>
              <div className="overflow-auto max-h-[360px]">
                <table className="min-w-full text-xs">
                  <thead className="sticky top-0 bg-surface-container-high z-10">
                    <tr className="text-left text-on-surface-variant uppercase tracking-wider">
                      {previewColumns.map((col) => (
                        <th key={col} className="px-3 py-2 border-b border-outline-variant/40 whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, index) => (
                      <tr key={index} className="border-b border-outline-variant/20">
                        {previewColumns.map((col) => (
                          <td key={col} className="px-3 py-2 whitespace-nowrap font-mono">
                            {row[col] ?? '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {err && (
            <div className="rounded-lg border border-error/40 bg-error/10 text-error p-4 text-sm">
              {err}
            </div>
          )}

          {validation && (
            <div className="rounded-lg border border-outline-variant/50 bg-surface-container-low p-5">
              <div className="flex items-center gap-2 font-bold">
                {validation.ok ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
                Resultado de validación
              </div>
              <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 text-sm">
                <div><dt className="text-on-surface-variant">Filas</dt><dd className="font-mono text-lg">{validation.total_rows}</dd></div>
                <div><dt className="text-on-surface-variant">Equipos</dt><dd className="font-mono text-lg">{validation.total_equipos}</dd></div>
                <div><dt className="text-on-surface-variant">Errores</dt><dd className="font-mono text-lg">{validation.errors.length}</dd></div>
                <div><dt className="text-on-surface-variant">Warnings</dt><dd className="font-mono text-lg">{validation.warnings.length}</dd></div>
              </dl>
              {[...validation.errors, ...validation.warnings].length > 0 && (
                <ul className="mt-4 space-y-2 text-sm">
                  {[...validation.errors, ...validation.warnings].map((item) => (
                    <li key={item} className="rounded border border-outline-variant/50 px-3 py-2">{item}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>

        <aside className="rounded-lg border border-outline-variant/50 bg-surface-container-low p-5 h-fit">
          <h2 className="text-sm font-bold uppercase tracking-widest text-on-surface-variant">
            Headers obligatorios
          </h2>
          <div className="mt-4 grid gap-2">
            {required.map((header) => (
              <code key={header} className="rounded border border-outline-variant/40 bg-surface px-2 py-1 text-xs">
                {header}
              </code>
            ))}
          </div>
        </aside>
      </div>
    </div>
  )
}
