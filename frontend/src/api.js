// Cliente HTTP — todas las llamadas al backend pasan por /api (proxy de Vite).
import { TOKEN_KEY } from './auth/AuthContext.jsx'

const BASE = '/api'

export function authHeaders(extra = {}) {
  const tok = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem(TOKEN_KEY) : null
  const h = { ...extra }
  if (tok) h.Authorization = `Bearer ${tok}`
  return h
}

async function request(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: authHeaders({
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
    }),
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
  health: () => request('/health'),

  variables: () => request('/variables'),
  listarEquipos: () => request('/equipos'),
  resumenFlota: () => request('/flota/resumen'),
  prediccion: (id) => request(`/equipos/${id}/prediccion`),
  historial: (id) => request(`/equipos/${id}/historial`),
  registrarMuestra: (id, body) =>
    request(`/equipos/${id}/muestras`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  me: () => request('/me'),

  adminUsers: () => request('/admin/users'),
  adminPatchRole: (userId, role) =>
    request(`/admin/users/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),

  exportar: (id, formato, fechaDesde = '', fechaHasta = '') => {
    const params = new URLSearchParams({ formato })
    if (fechaDesde) params.set('fecha_desde', fechaDesde)
    if (fechaHasta) params.set('fecha_hasta', fechaHasta)
    return fetch(`${BASE}/equipos/${id}/exportar?${params.toString()}`, {
      credentials: 'include',
      headers: authHeaders({ Accept: '*/*' }),
    })
  },
  exportarFlota: (formato) =>
    fetch(`${BASE}/flota/exportar?formato=${formato}`, {
      credentials: 'include',
      headers: authHeaders({ Accept: '*/*' }),
    }),
}
