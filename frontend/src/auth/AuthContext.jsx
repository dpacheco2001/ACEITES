import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

export const TOKEN_KEY = 'oilmine_access_token'

export function getAccessToken() {
  return typeof sessionStorage !== 'undefined' ? sessionStorage.getItem(TOKEN_KEY) : null
}

export function setAccessToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearAccessToken() {
  sessionStorage.removeItem(TOKEN_KEY)
}

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getAccessToken())
  const [profile, setProfile] = useState(() => {
    try {
      const raw = sessionStorage.getItem('oilmine_user_profile')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })

  const loginSession = useCallback(({ access_token: accessToken, user }) => {
    setAccessToken(accessToken)
    sessionStorage.setItem('oilmine_user_profile', JSON.stringify(user))
    setToken(accessToken)
    setProfile(user)
  }, [])

  const logout = useCallback(() => {
    clearAccessToken()
    sessionStorage.removeItem('oilmine_user_profile')
    setToken(null)
    setProfile(null)
  }, [])

  const hydrateProfileFromBackend = useCallback(async () => {
    const BASE = '/api'
    const t = getAccessToken()
    if (!t) return null
    const res = await fetch(`${BASE}/me`, {
      headers: {
        Authorization: `Bearer ${t}`,
        'Content-Type': 'application/json',
      },
    })
    if (res.status === 401) {
      logout()
      return null
    }
    if (!res.ok) {
      return null
    }
    const data = await res.json()
    const u = data.user
    sessionStorage.setItem('oilmine_user_profile', JSON.stringify(u))
    setProfile(u)
    return u
  }, [logout])

  useEffect(() => {
    const t = getAccessToken()
    if (!t) return
    hydrateProfileFromBackend().catch(() => {})
  }, [hydrateProfileFromBackend])

  const value = useMemo(
    () => ({
      token,
      profile,
      isAuthenticated: Boolean(token),
      loginSession,
      logout,
      hydrateProfileFromBackend,
    }),
    [token, profile, loginSession, logout, hydrateProfileFromBackend],
  )

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
