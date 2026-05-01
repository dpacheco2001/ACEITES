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
  const [memberships, setMemberships] = useState([])
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('CLIENTE')

  const load = useCallback(async () => {
    setErr(null)
    setLoading(true)
    try {
      const response = await api.adminUsers()
      setUsers(response.users || [])
      setMemberships(response.memberships || [])
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

  async function addMember(e) {
    e.preventDefault()
    setBusyId('new')
    setErr(null)
    try {
      await api.adminAddMember({ email, role })
      setEmail('')
      setRole('CLIENTE')
      await load()
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusyId(null)
    }
  }

  async function changeMembershipRole(id, role) {
    setBusyId(`m-${id}`)
    setErr(null)
    try {
      await api.adminPatchMemberRole(id, role)
      await load()
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusyId(null)
    }
  }

  const currentMembershipIds = new Set(
    memberships
      .filter((item) => item.user_id === profile?.id || item.email === profile?.email)
      .map((item) => item.id)
  )
  const pendingMemberships = memberships.filter((item) => (
    item.status !== 'ACTIVE' || !item.user_id
  ))

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
          {profile?.org_name || 'Organización'}: <span className="text-on-background">{profile?.tenant_key}</span>
        </p>
      </div>

      <form
        onSubmit={addMember}
        className="grid gap-3 md:grid-cols-[1fr_auto_auto] rounded-lg border border-outline-variant/50 bg-surface-container-low p-4"
      >
        <label className="text-sm">
          <span className="block text-xs uppercase tracking-widest text-on-surface-variant mb-1">
            Correo
          </span>
          <input
            className="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="usuario@empresa.com"
            required
          />
        </label>
        <label className="text-sm">
          <span className="block text-xs uppercase tracking-widest text-on-surface-variant mb-1">
            Rol
          </span>
          <select
            className="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            <option value="CLIENTE">CLIENTE</option>
            <option value="ADMIN">ADMIN</option>
          </select>
        </label>
        <button
          type="submit"
          disabled={busyId === 'new'}
          className="self-end rounded-lg bg-primary text-on-primary px-4 py-2 text-sm font-bold uppercase tracking-wider disabled:opacity-60"
        >
          Agregar
        </button>
      </form>

      {err && (
        <div className="rounded-lg border border-error/40 bg-error/10 text-error text-sm px-3 py-2">
          {err}
        </div>
      )}

      {loading ? (
        <p className="text-on-surface-variant">Cargando...</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-outline-variant/50 bg-surface-container-low">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-outline-variant/40 text-left text-on-surface-variant uppercase text-[10px] tracking-widest">
                <th className="p-3">Email</th>
                <th className="p-3">Rol</th>
                <th className="p-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-outline-variant/20">
                  <td className="p-3 font-mono text-xs">{user.email}</td>
                  <td className="p-3">{user.role}</td>
                  <td className="p-3">
                    {user.id === profile?.id ? (
                      <span className="text-on-surface-variant text-xs">(tu usuario)</span>
                    ) : (
                      <select
                        className="bg-surface border border-outline-variant rounded px-2 py-1 text-xs"
                        value={user.role}
                        disabled={busyId === user.id}
                        onChange={(e) => changeRole(user.id, e.target.value)}
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

      {!loading && pendingMemberships.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-outline-variant/50 bg-surface-container-low">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-outline-variant/40 text-left text-on-surface-variant uppercase text-[10px] tracking-widest">
                <th className="p-3">Invitación pendiente</th>
                <th className="p-3">Estado</th>
                <th className="p-3">Rol</th>
              </tr>
            </thead>
            <tbody>
              {pendingMemberships.map((item) => (
                <tr key={item.id} className="border-b border-outline-variant/20">
                  <td className="p-3 font-mono text-xs">{item.email}</td>
                  <td className="p-3">
                    <span className="rounded border border-outline-variant px-2 py-1 text-xs">
                      {item.status}
                    </span>
                  </td>
                  <td className="p-3">
                    {currentMembershipIds.has(item.id) ? (
                      <span className="text-on-surface-variant text-xs">
                        Rol protegido para tu sesión
                      </span>
                    ) : (
                      <select
                        className="bg-surface border border-outline-variant rounded px-2 py-1 text-xs"
                        value={item.role}
                        disabled={busyId === `m-${item.id}`}
                        onChange={(e) => changeMembershipRole(item.id, e.target.value)}
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
        Volver a Flota
      </Link>
    </div>
  )
}
