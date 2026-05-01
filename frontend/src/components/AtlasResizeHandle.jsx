import { Maximize2 } from 'lucide-react'

export default function AtlasResizeHandle({ resizeBy, resizeHandleProps }) {
  function handleKeyDown(event) {
    if (['ArrowUp', 'ArrowLeft', '+', '='].includes(event.key)) {
      event.preventDefault()
      resizeBy(1)
    }
    if (['ArrowDown', 'ArrowRight', '-', '_'].includes(event.key)) {
      event.preventDefault()
      resizeBy(-1)
    }
  }

  return (
    <button
      type="button"
      {...resizeHandleProps}
      onKeyDown={handleKeyDown}
      className="absolute -left-4 -top-4 z-20 flex h-9 w-9 touch-none cursor-nwse-resize items-center justify-center rounded-full border border-outline-variant/80 bg-surface-container-lowest text-on-surface shadow-[0_10px_28px_rgba(15,23,42,0.18)] ring-4 ring-surface/80 transition hover:-translate-x-0.5 hover:-translate-y-0.5 hover:bg-surface-container-low focus:outline focus:outline-2 focus:outline-primary-container/30"
      aria-label="Redimensionar Atlas"
      title="Redimensionar Atlas"
    >
      <Maximize2 size={15} strokeWidth={2.25} />
    </button>
  )
}
