"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import AuthTabs from "@/components/authTabs"
import { useAuth } from "@/components/authProvider"

export default function Auth() {
  const { status } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (status === "authenticated") router.replace("/")
  }, [status, router])

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      {status === "unauthenticated" && <AuthTabs />}
    </main>
  )
}
