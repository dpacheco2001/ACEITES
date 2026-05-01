import { useEffect, useState } from 'react'

export default function LoadingProgress({
  active,
  label = 'Cargando resultados',
  note = 'Atlas esperara estos resultados antes de explicar el dashboard.',
}) {
  const progress = useLoadingProgress(active)
  return (
    <div className="rounded-xl border border-outline-variant/60 bg-surface-container-lowest p-4 shadow-ambient">
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <span className="block text-sm font-semibold leading-5 text-on-surface">
            {label}
          </span>
          {note && (
            <span className="mt-1 block text-xs leading-5 text-on-surface-variant">
              {note}
            </span>
          )}
        </div>
        <span className="w-fit rounded-md border border-outline-variant/70 bg-surface px-2 py-1 font-mono text-[11px] text-on-surface-variant">
          {progress}%
        </span>
      </div>
      <div
        className="relative h-3 overflow-hidden rounded-full border border-outline-variant/60 bg-surface-container-high"
        role="progressbar"
        aria-label={label}
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={progress}
      >
        <div
          className="h-full rounded-full bg-[linear-gradient(90deg,#111827_0%,#4b5563_45%,#2563eb_100%)] transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
        <div className="pointer-events-none absolute inset-0 bg-[repeating-linear-gradient(135deg,rgba(255,255,255,0.35)_0,rgba(255,255,255,0.35)_8px,transparent_8px,transparent_16px)] opacity-30" />
      </div>
    </div>
  )
}

function useLoadingProgress(active) {
  const [progress, setProgress] = useState(8)

  useEffect(() => {
    if (!active) {
      setProgress(100)
      return undefined
    }
    setProgress(8)
    const timer = setInterval(() => {
      setProgress((value) => {
        if (value < 45) return value + 7
        if (value < 78) return value + 4
        if (value < 92) return value + 2
        return value
      })
    }, 280)
    return () => clearInterval(timer)
  }, [active])

  return progress
}
