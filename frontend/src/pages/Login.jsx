import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { clearAccessToken, useAuth } from '../auth/AuthContext.jsx'

async function exchangeGoogleCredential(idToken, loginSession, hydrateProfileFromBackend) {
  clearAccessToken()
  const res = await fetch('/api/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: idToken }),
  })
  if (!res.ok) {
    const txt = await res.text().catch(() => res.statusText)
    throw new Error(txt || `HTTP ${res.status}`)
  }
  const body = await res.json()
  loginSession(body)
  await hydrateProfileFromBackend()
}

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { loginSession, hydrateProfileFromBackend, token } = useAuth()
  const divRef = useRef(null)

  const envClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID || '').trim()
  const [clientId, setClientId] = useState(envClientId)
  const [configLoading, setConfigLoading] = useState(!envClientId)
  const [configError, setConfigError] = useState(null)

  // Client ID: Vite (.env.local) o, si falta, el mismo valor desde el backend (.env raíz).
  useEffect(() => {
    if (envClientId) {
      setConfigLoading(false)
      return undefined
    }
    let cancelled = false
    setConfigLoading(true)
    setConfigError(null)
    fetch('/api/auth/client-config')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => {
        if (cancelled) return
        const id = (data.google_client_id || '').trim()
        setClientId(id)
        if (!id) {
          setConfigError(
            'Configura GOOGLE_CLIENT_ID en el archivo .env de la raíz del proyecto (backend) y reinicia la API.',
          )
        }
      })
      .catch((e) => {
        if (!cancelled) setConfigError(e.message || 'No se pudo leer la configuración del servidor')
      })
      .finally(() => {
        if (!cancelled) setConfigLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [envClientId])

  useEffect(() => {
    if (token) {
      navigate((location.state && location.state.from) || '/', { replace: true })
    }
  }, [token, navigate, location.state])

  useEffect(() => {
    if (!clientId || !divRef.current) return undefined

    const init = () => {
      if (!(window.google && window.google.accounts && window.google.accounts.id)) return
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (resp) => {
          try {
            const cred = resp?.credential
            if (!cred) return
            await exchangeGoogleCredential(cred, loginSession, hydrateProfileFromBackend)
            navigate((location.state && location.state.from) || '/', { replace: true })
          } catch (e) {
            alert(e.message || 'Error en login')
          }
        },
        auto_select: false,
      })
      divRef.current.innerHTML = ''
      window.google.accounts.id.renderButton(divRef.current, {
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        locale: 'es',
      })
    }

    if (window.google && window.google.accounts) {
      init()
      return undefined
    }

    const existing = document.querySelector('script[src*="accounts.google.com/gsi/client"]')
    if (!existing) {
      const s = document.createElement('script')
      s.src = 'https://accounts.google.com/gsi/client'
      s.async = true
      s.defer = true
      s.onload = init
      document.head.appendChild(s)
    } else {
      existing.addEventListener('load', init)
      return () => existing.removeEventListener('load', init)
    }

    return undefined
  }, [clientId, loginSession, hydrateProfileFromBackend, navigate, location.state])

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-6 text-on-background">
      <div className="max-w-md w-full rounded-2xl border border-outline-variant/50 bg-surface-container-low p-8 shadow-ambient">
        <h1 className="text-xl font-bold tracking-tight mb-2">OilMine Analytics</h1>
        <p className="text-sm text-on-surface-variant mb-6">
          Entra con tu <strong>cuenta de Google</strong> (el correo debe estar verificado). Tu empresa se asigna
          automáticamente por el <strong>dominio del correo</strong> (ej.{' '}
          <span className="font-mono text-xs">usuario@empresa.com</span> → organización{' '}
          <span className="font-mono text-xs">empresa.com</span>). No hace falta que cada usuario configure nada: solo
          una vez en el servidor defines el Client ID de Google.
        </p>
        {configLoading && (
          <p className="text-sm text-on-surface-variant mb-4">Cargando configuración de inicio de sesión…</p>
        )}
        {configError && (
          <div className="rounded-lg bg-error/10 text-error text-sm p-3 border border-error/30 mb-4">
            {configError}
          </div>
        )}
        {!configLoading && !configError && clientId && (
          <div ref={divRef} className="flex justify-center" />
        )}
        {!configLoading && !clientId && !configError && (
          <div className="rounded-lg bg-error/10 text-error text-sm p-3 border border-error/30">
            Falta <code className="font-mono">GOOGLE_CLIENT_ID</code> en el <code className="font-mono">.env</code> del
            backend (raíz del proyecto). Reinicia <code className="font-mono">python run_api.py</code> tras guardarlo.
          </div>
        )}
      </div>
    </div>
  )
}
