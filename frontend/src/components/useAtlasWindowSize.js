import { useCallback, useEffect, useRef, useState } from 'react'

const STORAGE_KEY = 'oilmine.atlas.windowSize.v1'
const ASPECT_RATIO = 420 / 620
const DEFAULT_WIDTH = 420
const MIN_WIDTH = 340
const MAX_WIDTH = 860
const VIEWPORT_GAP = 40
const VERTICAL_RESERVED = 112
const STEP = 32

function viewportBounds() {
  if (typeof window === 'undefined') {
    return { width: DEFAULT_WIDTH, height: Math.round(DEFAULT_WIDTH / ASPECT_RATIO) }
  }

  const viewportWidth = Math.max(280, window.innerWidth - VIEWPORT_GAP)
  const viewportHeight = Math.max(360, window.innerHeight - VERTICAL_RESERVED)
  return {
    width: Math.min(MAX_WIDTH, viewportWidth, viewportHeight * ASPECT_RATIO),
    height: viewportHeight,
  }
}

function clampWidth(width) {
  const bounds = viewportBounds()
  const maxWidth = Math.max(280, bounds.width)
  const minWidth = Math.min(MIN_WIDTH, maxWidth)
  return Math.round(Math.min(maxWidth, Math.max(minWidth, width || DEFAULT_WIDTH)))
}

function sizeFromWidth(width) {
  const safeWidth = clampWidth(width)
  return {
    width: safeWidth,
    height: Math.round(safeWidth / ASPECT_RATIO),
  }
}

function readStoredSize() {
  if (typeof window === 'undefined') return sizeFromWidth(DEFAULT_WIDTH)

  try {
    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '{}')
    return sizeFromWidth(Number(stored.width) || DEFAULT_WIDTH)
  } catch {
    return sizeFromWidth(DEFAULT_WIDTH)
  }
}

export function useAtlasWindowSize() {
  const [size, setSize] = useState(readStoredSize)
  const [resizing, setResizing] = useState(false)
  const dragRef = useRef(null)

  useEffect(() => {
    const handleResize = () => setSize((current) => sizeFromWidth(current.width))
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ width: size.width }))
  }, [size.width])

  const startResize = useCallback((event) => {
    event.preventDefault()
    event.currentTarget.setPointerCapture?.(event.pointerId)
    dragRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      width: size.width,
      height: size.height,
    }
    setResizing(true)
  }, [size.height, size.width])

  const moveResize = useCallback((event) => {
    if (!dragRef.current) return
    const drag = dragRef.current
    const widthFromX = drag.width + drag.x - event.clientX
    const widthFromY = (drag.height + drag.y - event.clientY) * ASPECT_RATIO
    const nextWidth = Math.abs(widthFromX - drag.width) > Math.abs(widthFromY - drag.width)
      ? widthFromX
      : widthFromY
    setSize(sizeFromWidth(nextWidth))
  }, [])

  const stopResize = useCallback((event) => {
    if (dragRef.current?.pointerId === event.pointerId) {
      event.currentTarget.releasePointerCapture?.(event.pointerId)
    }
    dragRef.current = null
    setResizing(false)
  }, [])

  const resizeBy = useCallback((direction) => {
    setSize((current) => sizeFromWidth(current.width + direction * STEP))
  }, [])

  const resetSize = useCallback(() => {
    setSize(sizeFromWidth(DEFAULT_WIDTH))
  }, [])

  return {
    size,
    resizing,
    resizeBy,
    resetSize,
    resizeHandleProps: {
      onPointerDown: startResize,
      onPointerMove: moveResize,
      onPointerUp: stopResize,
      onPointerCancel: stopResize,
    },
  }
}
