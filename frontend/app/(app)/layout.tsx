"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/authProvider"
import { Button } from "@/components/ui/button"

/** Guards every route inside the (app) group: unauthenticated users go to /auth. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, status, logout } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/auth")
  }, [status, router])

  if (status !== "authenticated" || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground" aria-busy="true">
        Loading…
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b px-6 py-3">
        <span className="font-semibold tracking-tight">FinPilot</span>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">{user.email}</span>
          <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium">{user.role}</span>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </div>
  )
}
