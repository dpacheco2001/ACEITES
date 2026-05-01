import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

export default function AtlasImageModal({ image, onClose }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setVisible(true))
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') closeModal()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      window.cancelAnimationFrame(frame)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  function closeModal() {
    setVisible(false)
    window.setTimeout(onClose, 180)
  }

  return createPortal(
    <div
      className={`fixed inset-0 z-[120] flex items-center justify-center bg-black/60 p-4 transition-opacity duration-200 ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
      role="dialog"
      aria-modal="true"
      aria-label={image.alt}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) closeModal()
      }}
    >
      <div
        className={`flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-outline-variant/60 bg-surface-container-lowest shadow-[0_30px_90px_rgba(0,0,0,0.35)] transition-all duration-200 ${
          visible ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
        }`}
      >
        <header className="flex items-center justify-between gap-3 border-b border-outline-variant/60 bg-surface-container-low px-4 py-3">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-on-surface">{image.alt}</h3>
            {image.caption && (
              <p className="truncate text-xs text-on-surface-variant">{image.caption}</p>
            )}
          </div>
          <button
            type="button"
            onClick={closeModal}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg hover:bg-surface-container-high"
            aria-label="Cerrar grafico"
          >
            <X size={18} />
          </button>
        </header>
        <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto bg-surface p-4">
          <img
            src={image.src}
            alt={image.alt}
            className="max-h-[78vh] w-auto max-w-full rounded-lg border border-outline-variant/50 bg-white object-contain"
          />
        </div>
      </div>
    </div>,
    document.body,
  )
}
