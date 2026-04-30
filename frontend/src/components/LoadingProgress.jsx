import { useEffect, useState } from 'react'

export default function LoadingProgress({
  active,
  label = 'Cargando resultados',
  note = 'Atlas esperara estos resultados antes de explicar el dashboard.',
}) {
  const progress = useLoadingProgress(active)
  return (
    <div className="rounded-xl border border-outline-variant/50 bg-surface-container-lowest p-5 shadow-ambient">
      <div className="mb-3 flex items-center justify-between gap-4">
        <span className="text-sm font-semibold text-on-surface">{label}</span>
        <span className="font-mono text-xs text-on-surface-variant">{progress}%</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-surface-container-high"
        role="progressbar"
        aria-label={label}
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={progress}
      >
        <div
          className="h-full rounded-full bg-primary-container transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
      {note && <p className="mt-3 text-xs text-on-surface-variant">{note}</p>}
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
