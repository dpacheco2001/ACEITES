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
      className="absolute -left-3 -top-3 z-10 flex h-9 w-9 touch-none cursor-nwse-resize items-center justify-center rounded-lg border border-outline-variant/70 bg-surface-container-lowest text-on-surface shadow-lg hover:bg-surface-container-high focus:outline focus:outline-2 focus:outline-primary-container/30"
      aria-label="Redimensionar Atlas"
      title="Redimensionar Atlas"
    >
      <Maximize2 size={16} />
    </button>
  )
}
