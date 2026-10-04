"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import * as api from "@/lib/api"

type AuthStatus = "loading" | "authenticated" | "unauthenticated"

type AuthContextValue = {
  user: api.User | null
  status: AuthStatus
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<api.User | null>(null)
  const [status, setStatus] = useState<AuthStatus>("loading")

  // Restore the session on page load from the httpOnly refresh cookie.
  useEffect(() => {
    api
      .refreshSession()
      .then(({ user }) => {
        setUser(user)
        setStatus("authenticated")
      })
      .catch(() => setStatus("unauthenticated"))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setUser(await api.login(email, password))
    setStatus("authenticated")
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setUser(null)
      setStatus("unauthenticated")
    }
  }, [])

  const value = useMemo(
    () => ({ user, status, login, logout }),
    [user, status, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>")
  return ctx
}
