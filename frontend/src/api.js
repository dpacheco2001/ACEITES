// Cliente HTTP. La sesión viaja en cookie HttpOnly enviada con credentials.
const BASE = '/api'

async function request(path, opts = {}) {
  const headers = opts.body instanceof FormData
    ? { ...(opts.headers || {}) }
    : { 'Content-Type': 'application/json', ...(opts.headers || {}) }
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers,
    ...opts,
  })
  if (!res.ok) {
    let detail = await res.text().catch(() => res.statusText)
    try {
      const parsed = JSON.parse(detail)
      detail = parsed.detail?.message || parsed.detail || parsed.message || detail
    } catch {
      // keep raw text
    }
    const err = new Error(`${res.status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`)
    err.status = res.status
    throw err
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
  adminAddMember: (body) =>
    request('/admin/members', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  adminPatchRole: (userId, role) =>
    request(`/admin/users/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),
  adminPatchMemberRole: (membershipId, role) =>
    request(`/admin/members/${membershipId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),

  ownerOrganizations: () => request('/owner/organizations'),
  ownerCreateOrganization: (body) =>
    request('/owner/organizations', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  ownerTransfer: (body) =>
    request('/owner/owners/transfer', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  ownerDeleteOrganization: (orgId) =>
    request(`/owner/organizations/${orgId}`, {
      method: 'DELETE',
    }),

  datasetStatus: () => request('/org/dataset/status'),
  datasetPreview: () => request('/org/dataset/preview'),
  datasetDownloadUrl: () => `${BASE}/org/dataset/download`,
  datasetValidate: (file) => {
    const body = new FormData()
    body.append('file', file)
    return request('/org/dataset/validate', { method: 'POST', body })
  },
  datasetImport: (file) => {
    const body = new FormData()
    body.append('file', file)
    return request('/org/dataset/import', { method: 'POST', body })
  },

  exportar: (id, formato, fechaDesde = '', fechaHasta = '') => {
    const params = new URLSearchParams({ formato })
    if (fechaDesde) params.set('fecha_desde', fechaDesde)
    if (fechaHasta) params.set('fecha_hasta', fechaHasta)
    return fetch(`${BASE}/equipos/${id}/exportar?${params.toString()}`, {
      credentials: 'include',
      headers: { Accept: '*/*' },
    })
  },
  exportarFlota: (formato) =>
    fetch(`${BASE}/flota/exportar?formato=${formato}`, {
      credentials: 'include',
      headers: { Accept: '*/*' },
    }),
}
