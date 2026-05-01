import { useCallback, useEffect, useMemo, useState } from 'react'
import { Building2, Database, RefreshCw, ShieldPlus, Trash2, UserRoundCog, Users } from 'lucide-react'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'

const initialForm = {
  name: '',
  admin_email: '',
}

export default function OwnerOrganizaciones() {
  const { profile } = useAuth()
  const [items, setItems] = useState([])
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [ownerEmail, setOwnerEmail] = useState('')
  const [busyOrgId, setBusyOrgId] = useState(null)
  const [err, setErr] = useState(null)

  const load = useCallback(async () => {
    setErr(null)
    setLoading(true)
    try {
      const response = await api.ownerOrganizations()
      setItems(response.organizations || [])
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const totals = useMemo(() => ({
    orgs: items.length,
    users: items.reduce((sum, item) => sum + item.user_count, 0),
    datasets: items.filter((item) => item.dataset_loaded).length,
  }), [items])

  async function createOrganization(event) {
    event.preventDefault()
    setSaving(true)
    setErr(null)
    try {
      await api.ownerCreateOrganization({
        name: form.name,
        admin_email: form.admin_email,
      })
      setForm(initialForm)
      await load()
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setSaving(false)
    }
  }

  async function transferOwner(event) {
    event.preventDefault()
    setSaving(true)
    setErr(null)
    try {
      await api.ownerTransfer({ email: ownerEmail })
      setOwnerEmail('')
      await load()
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setSaving(false)
    }
  }

  async function deleteOrganization(item) {
    const ok = window.confirm(`Desactivar ${item.name || item.tenant_key}?`)
    if (!ok) return
    setBusyOrgId(item.id)
    setErr(null)
    try {
      await api.ownerDeleteOrganization(item.id)
      await load()
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusyOrgId(null)
    }
  }

  if (!profile?.is_owner) {
    return (
      <section className="mx-auto max-w-3xl p-6 md:p-10">
        <p className="text-sm text-on-surface-variant">Esta sección es solo para owner.</p>
      </section>
    )
  }

  return (
    <section className="p-6 md:p-10">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="flex flex-col gap-4 border-b border-outline-variant/60 pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-on-surface-variant">
              Owner Console
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-on-background">
              Organizaciones OilMine
            </h1>
          </div>
          <button
            type="button"
            onClick={load}
            className="inline-flex w-fit items-center gap-2 rounded-lg border border-outline-variant/70 bg-surface px-3 py-2 text-sm font-semibold hover:bg-surface-container-high"
          >
            <RefreshCw size={16} />
            Refrescar
          </button>
        </header>

        <div className="grid gap-3 md:grid-cols-3">
          <Metric icon={Building2} label="Organizaciones" value={totals.orgs} />
          <Metric icon={Users} label="Usuarios activos" value={totals.users} />
          <Metric icon={Database} label="Datasets cargados" value={totals.datasets} />
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_0.85fr]">
          <form
            onSubmit={createOrganization}
            className="grid gap-3 rounded-lg border border-outline-variant/60 bg-surface-container-low p-4 md:grid-cols-[1fr_1fr_auto]"
          >
            <Field
              label="Nombre"
              value={form.name}
              placeholder="Veyon"
              onChange={(name) => setForm((prev) => ({ ...prev, name }))}
            />
            <Field
              label="Admin inicial"
              type="email"
              value={form.admin_email}
              placeholder="admin@empresa.com"
              onChange={(admin_email) => setForm((prev) => ({ ...prev, admin_email }))}
            />
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 self-end rounded-lg bg-primary px-4 py-2 text-sm font-bold text-on-primary disabled:opacity-60"
            >
              <ShieldPlus size={16} />
              Crear
            </button>
          </form>

          <form
            onSubmit={transferOwner}
            className="grid gap-3 rounded-lg border border-outline-variant/60 bg-surface-container-low p-4 md:grid-cols-[1fr_auto]"
          >
            <Field
              label="Transferir owner a"
              type="email"
              value={ownerEmail}
              placeholder="owner@empresa.com"
              onChange={setOwnerEmail}
            />
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 self-end rounded-lg border border-outline-variant bg-surface px-4 py-2 text-sm font-bold hover:bg-surface-container-high disabled:opacity-60"
            >
              <UserRoundCog size={16} />
              Transferir
            </button>
          </form>
        </div>

        {err && (
          <div className="rounded-lg border border-error/40 bg-error/10 px-3 py-2 text-sm text-error">
            {err}
          </div>
        )}

        <div className="overflow-hidden rounded-lg border border-outline-variant/60 bg-surface">
          <table className="w-full min-w-[820px] text-sm">
            <thead className="bg-surface-container-low text-left text-[10px] uppercase tracking-widest text-on-surface-variant">
              <tr>
                <th className="px-4 py-3">Organización</th>
                <th className="px-4 py-3">Admin</th>
                <th className="px-4 py-3">Usuarios</th>
                <th className="px-4 py-3">Dataset</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Acción</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td className="px-4 py-8 text-on-surface-variant" colSpan={6}>
                    Cargando organizaciones...
                  </td>
                </tr>
              ) : items.map((item) => (
                <tr key={item.id} className="border-t border-outline-variant/40">
                  <td className="px-4 py-3">
                    <div className="font-semibold text-on-background">{item.name}</div>
                    <div className="font-mono text-xs text-on-surface-variant">{item.tenant_key}</div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {item.admin_emails.join(', ') || 'Sin admin asignado'}
                  </td>
                  <td className="px-4 py-3">{item.user_count}</td>
                  <td className="px-4 py-3">
                    {item.dataset_loaded
                      ? `${item.dataset_rows} filas · ${item.dataset_equipos} equipos`
                      : 'Pendiente'}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-md border border-outline-variant/70 px-2 py-1 text-xs">
                      {item.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {item.status === 'ACTIVE' ? (
                      <button
                        type="button"
                        disabled={busyOrgId === item.id || item.id === profile.org_id}
                        onClick={() => deleteOrganization(item)}
                        className="inline-flex items-center gap-2 rounded-md border border-error/30 px-2 py-1 text-xs text-error hover:bg-error/10 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <Trash2 size={13} />
                        Desactivar
                      </button>
                    ) : (
                      <span className="text-xs text-on-surface-variant">Soft delete</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

function Field({ label, value, onChange, placeholder, type = 'text' }) {
  return (
    <label className="text-sm">
      <span className="mb-1 block text-xs uppercase tracking-widest text-on-surface-variant">
        {label}
      </span>
      <input
        className="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2"
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required
      />
    </label>
  )
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between border-b border-outline-variant/60 py-3">
      <div className="flex items-center gap-3">
        <Icon size={18} className="text-on-surface-variant" />
        <span className="text-sm text-on-surface-variant">{label}</span>
      </div>
      <span className="font-mono text-xl font-semibold text-on-background">{value}</span>
    </div>
  )
}
