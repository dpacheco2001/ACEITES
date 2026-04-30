import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const PROFILE_KEY = 'oilmine_user_profile'

function readStoredProfile() {
  try {
    const raw = sessionStorage.getItem(PROFILE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function storeProfile(profile) {
  if (profile) {
    sessionStorage.setItem(PROFILE_KEY, JSON.stringify(profile))
  } else {
    sessionStorage.removeItem(PROFILE_KEY)
  }
}

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [profile, setProfile] = useState(() => readStoredProfile())
  const [loading, setLoading] = useState(true)

  const clearSession = useCallback(() => {
    storeProfile(null)
    setProfile(null)
  }, [])

  const loginSession = useCallback(({ user }) => {
    storeProfile(user)
    setProfile(user)
  }, [])

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      })
    } finally {
      clearSession()
    }
  }, [clearSession])

  const hydrateProfileFromBackend = useCallback(async () => {
    const res = await fetch('/api/me', {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
    if (res.status === 401) {
      clearSession()
      return null
    }
    if (!res.ok) {
      clearSession()
      return null
    }
    const data = await res.json()
    const user = data.user
    storeProfile(user)
    setProfile(user)
    return user
  }, [clearSession])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    hydrateProfileFromBackend()
      .catch(() => {
        if (!cancelled) clearSession()
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [clearSession, hydrateProfileFromBackend])

  const value = useMemo(
    () => ({
      profile,
      loading,
      isAuthenticated: Boolean(profile),
      loginSession,
      logout,
      hydrateProfileFromBackend,
    }),
    [profile, loading, loginSession, logout, hydrateProfileFromBackend],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
