"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { AccountCards } from "@/components/dashboard/accountCards"
import { AllocationChart } from "@/components/dashboard/allocationChart"
import { GoalsSummary } from "@/components/dashboard/goalsSummary"
import { PortfolioSummary } from "@/components/dashboard/portfolioSummary"
import { PositionsTable } from "@/components/dashboard/positionsTable"
import { RecentTransactions } from "@/components/dashboard/recentTransactions"
import { RiskSummary } from "@/components/dashboard/riskSummary"
import { EmptyState, ErrorState, LoadingRows } from "@/components/states"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useCustomer, useGoals, usePortfolio } from "@/lib/queries"

export default function CustomerDashboardPage() {
  const { id } = useParams<{ id: string }>()
  const customer = useCustomer(id)
  const portfolio = usePortfolio(id)
  const goals = useGoals(id)

  // Header, tabs and "not found" live in layout.tsx. Each section below loads
  // and fails independently, so one slow query never blanks the page.
  return (
    <div className="space-y-6">
      {portfolio.isPending ? (
        <Skeleton className="h-36 w-full" />
      ) : portfolio.isError ? (
        <ErrorState error={portfolio.error} onRetry={portfolio.refetch} />
      ) : (
        <PortfolioSummary portfolio={portfolio.data} />
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Asset allocation</CardTitle>
          </CardHeader>
          <CardContent>
            {portfolio.isPending ? (
              <LoadingRows rows={4} />
            ) : portfolio.isError ? null : portfolio.data.allocation.length === 0 ? (
              <EmptyState title="Nothing to allocate" description="This customer has no positions in the latest snapshot." />
            ) : (
              <AllocationChart allocation={portfolio.data.allocation} />
            )}
          </CardContent>
        </Card>
        {customer.isPending ? (
          <Skeleton className="h-64 w-full" />
        ) : customer.isError ? null : (
          <RiskSummary risk={customer.data.latest_risk_profile} />
        )}
      </div>

      <section aria-labelledby="accounts-heading" className="space-y-3">
        <h2 id="accounts-heading" className="text-lg font-semibold">Accounts</h2>
        {portfolio.isPending ? <LoadingRows rows={2} /> : portfolio.isError ? null : <AccountCards accounts={portfolio.data.accounts} />}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {goals.isPending ? (
          <LoadingRows rows={4} />
        ) : goals.isError ? (
          <ErrorState error={goals.error} onRetry={goals.refetch} />
        ) : (
          <GoalsSummary
            goals={goals.data}
            action={<Link href={`/customers/${id}/goals`} className="text-sm text-muted-foreground hover:text-foreground hover:underline">Manage goals</Link>}
          />
        )}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent activity</CardTitle>
            <Link href={`/customers/${id}/transactions`} className="text-sm text-muted-foreground hover:text-foreground hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent>
            <RecentTransactions customerId={id} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
        </CardHeader>
        <CardContent>
          {portfolio.isPending ? <LoadingRows rows={6} /> : portfolio.isError ? null : <PositionsTable positions={portfolio.data.positions} />}
        </CardContent>
      </Card>
    </div>
  )
}

