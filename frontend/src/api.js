// Cliente HTTP — todas las llamadas al backend pasan por /api (proxy de Vite).
const BASE = '/api'

async function request(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${msg}`)
  }
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res.blob()
}

export const api = {
  health:         ()                 => request('/health'),
  variables:      ()                 => request('/variables'),
  listarEquipos:  ()                 => request('/equipos'),
  resumenFlota:   ()                 => request('/flota/resumen'),
  prediccion:     (id)               => request(`/equipos/${id}/prediccion`),
  historial:      (id)               => request(`/equipos/${id}/historial`),
  registrarMuestra: (id, body)       => request(`/equipos/${id}/muestras`, {
    method: 'POST', body: JSON.stringify(body),
  }),
  exportar:       (id, formato, fechaDesde = '', fechaHasta = '') => {
    const params = new URLSearchParams({ formato })
    if (fechaDesde) params.set('fecha_desde', fechaDesde)
    if (fechaHasta) params.set('fecha_hasta', fechaHasta)
    return fetch(`${BASE}/equipos/${id}/exportar?${params.toString()}`)
  },
  exportarFlota:  (formato)          =>
    fetch(`${BASE}/flota/exportar?formato=${formato}`),
}
