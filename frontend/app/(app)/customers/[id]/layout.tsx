"use client"

import Link from "next/link"
import { useParams, usePathname } from "next/navigation"
import { ArrowLeftIcon } from "lucide-react"
import { cn } from "cn"
import { CustomerHeader } from "@/components/dashboard/customerHeader"
import { EmptyState, ErrorState } from "@/components/states"
import { Skeleton } from "@/components/ui/skeleton"
import { ApiError } from "@/lib/api"
import { useCustomer } from "@/lib/queries"

/** Shared header + tabs for every page about one customer. */
export default function CustomerLayout({ children }: { children: React.ReactNode }) {
  const { id } = useParams<{ id: string }>()
  const pathname = usePathname()
  const customer = useCustomer(id)

  const tabs = [
    { href: `/customers/${id}`, label: "Overview" },
    { href: `/customers/${id}/transactions`, label: "Transactions" },
    { href: `/customers/${id}/goals`, label: "Goals" },
  ]

  if (customer.error instanceof ApiError && customer.error.status === 404) {
    return (
      <div className="space-y-4">
        <BackLink />
        <EmptyState title={`Customer ${id} not found`} description="Check the ID or search again." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <BackLink />
      {customer.isPending ? (
        <Skeleton className="h-14 w-96 max-w-full" />
      ) : customer.isError ? (
        <ErrorState error={customer.error} onRetry={customer.refetch} />
      ) : (
        <CustomerHeader customer={customer.data} />
      )}
      <nav aria-label="Customer sections" className="flex gap-1 border-b">
        {tabs.map((tab) => {
          const active = pathname === tab.href
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "-mb-px border-b-2 px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground",
                active ? "border-foreground text-foreground" : "border-transparent",
              )}
            >
              {tab.label}
            </Link>
          )
        })}
      </nav>
      {children}
    </div>
  )
}

function BackLink() {
  return (
    <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeftIcon className="size-4" /> All customers
    </Link>
  )
}
