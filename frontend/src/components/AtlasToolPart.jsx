import {
  AlertTriangle,
  BarChart3,
  Brain,
  CheckCircle2,
  Code2,
  Database,
  FileStack,
  Image,
  Loader2,
  Wrench,
} from 'lucide-react'

const TOOL_META = {
  getModelContext: { label: 'Contexto ML', icon: Brain },
  getDashboardResults: { label: 'Dashboard', icon: BarChart3 },
  getEquipmentResults: { label: 'Equipo', icon: Database },
  createDatasetSlice: { label: 'Slice de datos', icon: FileStack },
  runPythonAnalysis: { label: 'Python', icon: Code2 },
  showImage: { label: 'Imagen', icon: Image },
  listRunArtifacts: { label: 'Artefactos', icon: FileStack },
}

export default function AtlasToolPart({ part }) {
  const name = part.toolName || String(part.type).replace(/^tool-/, '')
  const state = part.state || 'input-available'
  const output = part.output || part.result
  const meta = TOOL_META[name] || { label: name, icon: Wrench }
  const Icon = meta.icon
  const isRunning = state === 'input-streaming' || state === 'input-available'
  const isError = state === 'output-error' || output?.ok === false || output?.error
  const image = output?.image
  const artifactUrl = image?.url ? `/atlas-api${image.url}` : null

  return (
    <div className="mt-2 rounded-lg border border-outline-variant/50 bg-surface-container-low p-2 text-xs text-on-surface-variant">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-container-high text-on-surface">
            <Icon size={14} strokeWidth={2} />
          </span>
          <span className="truncate font-mono text-on-surface">{meta.label}</span>
        </div>
        <ToolState isError={isError} isRunning={isRunning} state={state} />
      </div>

      {isRunning && (
        <p className="mt-2 font-mono text-[11px]">
          Espera que carguen los resultados antes de concluir.
        </p>
      )}
      {isError && (
        <p className="mt-2 text-error">{part.errorText || output?.error || 'Tool failed'}</p>
      )}
      {output?.row_count_returned != null && (
        <p className="mt-2">Slice: {output.row_count_returned} filas</p>
      )}
      {artifactUrl && (
        <figure className="mt-2">
          <img
            src={artifactUrl}
            alt={output.caption || image.filename || 'Grafico Atlas'}
            className="w-full rounded-lg border border-outline-variant/50"
          />
          {output.caption && <figcaption className="mt-1">{output.caption}</figcaption>}
        </figure>
      )}
    </div>
  )
}

function ToolState({ isError, isRunning, state }) {
  if (isRunning) {
    return (
      <span className="inline-flex items-center gap-1 font-mono uppercase">
        <Loader2 size={13} className="animate-spin" />
        Running
      </span>
    )
  }
  if (isError) {
    return (
      <span className="inline-flex items-center gap-1 font-mono uppercase text-error">
        <AlertTriangle size={13} />
        Error
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 font-mono uppercase">
      <CheckCircle2 size={13} />
      {state === 'output-available' ? 'Done' : state}
    </span>
  )
}
