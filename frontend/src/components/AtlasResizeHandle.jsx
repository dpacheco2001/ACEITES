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
      className="absolute bottom-2 left-2 z-10 h-5 w-5 touch-none cursor-nesw-resize rounded-sm opacity-40 transition-opacity hover:opacity-100 focus:opacity-100 focus:outline focus:outline-2 focus:outline-primary-container/30"
      aria-label="Redimensionar Atlas"
      title="Redimensionar Atlas"
    >
      <span className="absolute bottom-1 left-1 h-2.5 w-2.5 border-b-2 border-l-2 border-outline" />
      <span className="absolute bottom-1 left-1 h-4 w-4 border-b-2 border-l-2 border-outline" />
    </button>
  )
}
