import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'

export default function AdminUsuarios() {
  const { profile } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setErr(null)
    setLoading(true)
    try {
      const r = await api.adminUsers()
      setUsers(r.users || [])
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function changeRole(userId, role) {
    setBusyId(userId)
    setErr(null)
    try {
      await api.adminPatchRole(userId, role)
      await load()
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusyId(null)
    }
  }

  if (profile?.role !== 'ADMIN') {
    return (
      <div className="max-w-xl mx-auto p-6 md:p-8 space-y-4">
        <p className="text-on-surface-variant">No tienes permisos para ver esta sección.</p>
        <Link to="/" className="text-surface-tint underline">Volver a Flota</Link>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto p-4 md:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-on-background">Usuarios de la organización</h1>
        <p className="text-sm text-on-surface-variant mt-1 font-mono">
          Dominio: <span className="text-on-background">{profile?.tenant_key}</span>
        </p>
      </div>

      {err && (
        <div className="rounded-lg border border-error/40 bg-error/10 text-error text-sm px-3 py-2">
          {err}
        </div>
      )}

      {loading ? (
        <p className="text-on-surface-variant">Cargando…</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-outline-variant/50 bg-surface-container-low">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-outline-variant/40 text-left text-on-surface-variant uppercase text-[10px] tracking-widest">
                <th className="p-3">Email</th>
                <th className="p-3">Rol</th>
                <th className="p-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-outline-variant/20">
                  <td className="p-3 font-mono text-xs">{u.email}</td>
                  <td className="p-3">{u.role}</td>
                  <td className="p-3">
                    {u.id === profile?.id ? (
                      <span className="text-on-surface-variant text-xs">(tú)</span>
                    ) : (
                      <select
                        className="bg-surface border border-outline-variant rounded px-2 py-1 text-xs"
                        value={u.role}
                        disabled={busyId === u.id}
                        onChange={(e) => changeRole(u.id, e.target.value)}
                      >
                        <option value="CLIENTE">CLIENTE</option>
                        <option value="ADMIN">ADMIN</option>
                      </select>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Link to="/" className="inline-block text-sm text-surface-tint underline">
        ← Volver a Flota
      </Link>
    </div>
  )
}
