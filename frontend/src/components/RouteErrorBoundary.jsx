import { Component } from 'react'

function isChunkError(error) {
  const text = String(error?.message || error || '')
  return (
    text.includes('Failed to fetch dynamically imported module') ||
    text.includes('Importing a module script failed') ||
    text.includes('error loading dynamically imported module')
  )
}

export default class RouteErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error) {
    if (!isChunkError(error)) return
    const key = 'oilmine_chunk_reload_once'
    if (sessionStorage.getItem(key) === '1') return
    sessionStorage.setItem(key, '1')
    window.location.reload()
  }

  componentDidUpdate() {
    if (!this.state.error) {
      sessionStorage.removeItem('oilmine_chunk_reload_once')
    }
  }

  render() {
    if (!this.state.error) return this.props.children
    if (isChunkError(this.state.error)) {
      return (
        <div className="min-h-screen grid place-items-center bg-background text-on-background p-6">
          <button
            type="button"
            className="rounded-lg bg-primary text-on-primary px-4 py-2 text-sm font-bold"
            onClick={() => window.location.reload()}
          >
            Actualizar aplicación
          </button>
        </div>
      )
    }
    throw this.state.error
  }
}
