"use client"

import { useEffect } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { cn } from "cn"
import { useAuth } from "@/components/authProvider"
import { Button } from "@/components/ui/button"

const NAV = [
  { href: "/", label: "Customers", adminOnly: false },
  { href: "/admin/imports", label: "Imports", adminOnly: true },
]

/** Guards every route inside the (app) group: unauthenticated users go to /auth. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, status, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

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

  const isActive = (href: string) => (href === "/" ? pathname === "/" || pathname.startsWith("/customers") : pathname.startsWith(href))

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-3">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-semibold tracking-tight">
            FinPilot
          </Link>
          <nav aria-label="Main" className="flex gap-1 text-sm">
            {NAV.filter((item) => !item.adminOnly || user.role === "ADMIN").map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive(item.href) ? "page" : undefined}
                className={cn(
                  "rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  isActive(item.href) && "bg-muted text-foreground",
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">{user.email}</span>
          <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium">{user.role}</span>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 p-6">{children}</main>
    </div>
  )
}
